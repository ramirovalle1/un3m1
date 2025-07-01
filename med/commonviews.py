# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from decorators import last_access
from med.forms import EntregaProductosConsultaForm
from med.models import InventarioMedicoLote, TIPOINVENTARIOMEDICO_CHOICES, PersonaConsultaMedica, \
    PersonaConsultaOdontologica, PersonaConsultaPsicologica, InventarioMedicoMovimiento
from sga.commonviews import adduserdata, obtener_reporte


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@transaction.atomic()
def box_inventario(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'datoproducto':
            try:
                producto = InventarioMedicoLote.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'id': producto.id, 'codigo': producto.inventariomedico.codigobarra, 'descripcion': producto.inventariomedico.descripcion, 'numero': producto.numero, 'cantidad': producto.cantidad, 'tipo': TIPOINVENTARIOMEDICO_CHOICES[producto.inventariomedico.tipo - 1][1]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'productosusados':
            try:
                if 'idcm' in request.POST:
                    consulta = PersonaConsultaMedica.objects.get(pk=request.POST['idcm'])
                    documento = "CONSMED-" + str(consulta.id)
                elif 'idco' in request.POST:
                    consulta = PersonaConsultaOdontologica.objects.get(pk=request.POST['idco'])
                    documento = "CONSODN-" + str(consulta.id)
                else:
                    consulta = PersonaConsultaPsicologica.objects.get(pk=request.POST['idcp'])
                    documento = "CONSPSI-" + str(consulta.id)
                lista = request.POST['lista'].split(',')
                for elemento in lista:
                    producto = InventarioMedicoLote.objects.get(pk=int(elemento.split(':')[0]))
                    cantidad = int(elemento.split(':')[1])
                    movimiento = InventarioMedicoMovimiento(inventariomedicolote=producto,
                                                            numerodocumento=documento,
                                                            tipo=2,
                                                            fecha=consulta.fecha,
                                                            cantidad=cantidad,
                                                            entrega=consulta.medico,
                                                            consultamedica=consulta if 'idcm' in request.POST else None,
                                                            consultaodontologica=consulta if 'idco' in request.POST else None,
                                                            consultapsicologica=consulta if 'idcp' in request.POST else None,
                                                            recibe=consulta.persona,
                                                            detalle='ENTREGA DE MATERIAL O MEDICAMENTOS')
                    movimiento.save(request)
                    producto.cantidad -= cantidad
                    producto.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        action = request.GET['action']

        if action == 'productosusados':
            try:
                data['title'] = u'Materiales y medicamentos utilizados en la consulta'
                if 'idcm' in request.GET:
                    consulta = PersonaConsultaMedica.objects.get(pk=request.GET['idcm'])
                    data['idcm'] = request.GET['idcm']
                elif 'idco' in request.GET:
                    consulta = PersonaConsultaOdontologica.objects.get(pk=request.GET['idco'])
                    data['idco'] = request.GET['idco']
                else:
                    consulta = PersonaConsultaPsicologica.objects.get(pk=request.GET['idcp'])
                    data['idcp'] = request.GET['idcp']
                data['consulta'] = consulta
                data['form'] = EntregaProductosConsultaForm()
                data['paciente'] = consulta.persona
                return render(request, "box_inventario/productosusados.html", data)
            except Exception as ex:
                pass

        if action == 'productosentregados':
            try:
                data['title'] = u'Materiales y medicamentos entregados en la consulta'
                if 'idcm' in request.GET:
                    consulta = PersonaConsultaMedica.objects.get(pk=request.GET['idcm'])
                    data['idcm'] = request.GET['idcm']
                elif 'idco' in request.GET:
                    consulta = PersonaConsultaOdontologica.objects.get(pk=request.GET['idco'])
                    data['idco'] = request.GET['idco']
                else:
                    consulta = PersonaConsultaPsicologica.objects.get(pk=request.GET['idcp'])
                    data['idcp'] = request.GET['idcp']
                data['consulta'] = consulta
                data['paciente'] = consulta.persona
                data['productos'] = consulta.productos_usados()
                data['reporte_0'] = obtener_reporte('lista_productos_entregados')
                return render(request, "box_inventario/productosentregados.html", data)
            except Exception as ex:
                pass

        return HttpResponseRedirect('/')