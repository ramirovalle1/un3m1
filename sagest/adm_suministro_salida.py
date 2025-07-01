# -*- coding: UTF-8 -*-

import json
from datetime import datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.forms import SuministroSalidaProductoForm, SuministroDetalleSalidaProductoForm
from sagest.models import Producto, Departamento, SuministroSalidaProducto, DetalleSuministroSalidaProducto
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, MiPaginador, puede_realizar_accion


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = SuministroSalidaProductoForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    salidaprod = SuministroSalidaProducto(departamento=f.cleaned_data['departamento'],
                                                          responsable=f.cleaned_data['responsable'],
                                                          fechaoperacion=datetime.now(),
                                                          descripcion=f.cleaned_data['descripcion'],
                                                          observaciones=f.cleaned_data['observaciones'])
                    salidaprod.save(request)
                    for elemento in datos:
                        producto = Producto.objects.get(pk=int(elemento['id']))
                        detallesalprod = DetalleSuministroSalidaProducto(producto=producto,
                                                                         cantidad=Decimal(elemento['cantidad']).quantize(Decimal('.0001')))
                        detallesalprod.save(request)
                        salidaprod.productos.add(detallesalprod)
                        # ACTUALIZAR INVENTARIO REAL
                    salidaprod.save(request)
                    log(u'Adiciono nuevo suministro de salida de inventario: %s' % salidaprod, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'buscarresponsable':
            try:
                departamento = Departamento.objects.get(pk=int(request.POST['id']))
                lista = []
                for integrante in departamento.integrantes.all():
                    lista.append([integrante.id, integrante.nombre_completo_inverso()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'chequeacodigos':
            try:
                cod_existen = [x.codigo for x in Producto.objects.filter(codigo__in=request.POST['codigos'].split(","))]
                if cod_existen:
                    return JsonResponse({"result": "ok", "codigosexisten": cod_existen})
                return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'comprobarnumero':
            try:
                departamento = Departamento.objects.get(pk=request.POST['pid'])
                numero = request.POST['numero']
                if departamento.suministrosalidaproducto_set.filter(numero=numero).exists():
                    return JsonResponse({"result": "bad"})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'detalle_salida':
            try:
                data['salida'] = salida = SuministroSalidaProducto.objects.get(pk=request.POST['id'])
                data['detalles'] = salida.productos.all()
                template = get_template("adm_suministro_salida/detallesalidas.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'numero': salida.numerodocumento})
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Salidas de Suministros'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sagest.puede_dar_salida_suministro')
                    ultimo = 1
                    try:
                        ultimo = SuministroSalidaProducto.objects.all().order_by("-id")[0].numerodocumento
                        ultimo = int(ultimo) + 1
                    except:
                        pass
                    form = SuministroSalidaProductoForm(initial={'numerodocumento': str(ultimo)})
                    form.adicionar()
                    data['form'] = form
                    form2 = SuministroDetalleSalidaProductoForm()
                    form2.adicionar()
                    data['form2'] = form2
                    return render(request, "adm_suministro_salida/add.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                salidas = SuministroSalidaProducto.objects.filter(Q(departamento__nombre__icontains=search) |
                                                        Q(numerodocumento__icontains=search) |
                                                        Q(descripcion__icontains=search) |
                                                        Q(observaciones__icontains=search))
            elif 'id' in request.GET:
                ids = request.GET['id']
                salidas = SuministroSalidaProducto.objects.filter(id=ids)
            else:
                salidas = SuministroSalidaProducto.objects.all()
            paging = MiPaginador(salidas, 25)
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
            data['reporte_0'] = obtener_reporte('comprobante_egreso_suministro')
            data['salidas'] = page.object_list
            return render(request, "adm_suministro_salida/view.html", data)