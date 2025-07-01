# -*- coding: UTF-8 -*-
import calendar
import statistics
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Max, Sum
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import ProductoForm,PeligrosidadProductoForm
from sagest.models import Producto, TipoProducto, null_to_numeric, PeligrosidadProducto, KardexInventario
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, puede_realizar_accion,log
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    hoy=datetime.now()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ProductoForm(request.POST)
                if f.is_valid():
                    cuenta = f.cleaned_data['cuenta']
                    ultimo = null_to_numeric(Producto.objects.filter(cuenta=cuenta).aggregate(maximo=Max('codigo'))['maximo'])
                    producto = Producto(codigo=ultimo + 1,
                                        descripcion=f.cleaned_data['descripcion'],
                                        unidadmedida=f.cleaned_data['unidadmedida'],
                                        tipoproducto=f.cleaned_data['tipoproducto'],
                                        cuenta=f.cleaned_data['cuenta'],
                                        alias=f.cleaned_data['alias'],
                                        codigobarra=f.cleaned_data['codigobarra'],
                                        minimo=f.cleaned_data['minimo'],
                                        maximo=f.cleaned_data['maximo'],
                                        consumo_minimo_diario=f.cleaned_data['consumo_minimo_diario'],
                                        consumo_medio_diario=f.cleaned_data['consumo_medio_diario'],
                                        consumo_maximo_diario=f.cleaned_data['consumo_maximo_diario'],
                                        tiempo_reposicion_inventario=f.cleaned_data['tiempo_reposicion_inventario'],
                                        peligrosidad=f.cleaned_data['peligrosidad'],
                                        )
                    producto.save(request)
                    log(u'Ingreso Producto : %s' % producto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                producto = Producto.objects.get(pk=request.POST['id'])
                f = ProductoForm(request.POST)
                if f.is_valid():
                    producto.minimo = f.cleaned_data['minimo']
                    producto.maximo = f.cleaned_data['maximo']
                    producto.consumo_minimo_diario = f.cleaned_data['consumo_minimo_diario']
                    producto.consumo_medio_diario = f.cleaned_data['consumo_medio_diario']
                    producto.consumo_maximo_diario = f.cleaned_data['consumo_maximo_diario']
                    producto.tiempo_reposicion_inventario = f.cleaned_data['tiempo_reposicion_inventario']
                    if not producto.en_uso():
                        producto.tipoproducto = f.cleaned_data['tipoproducto']
                        producto.descripcion = f.cleaned_data['descripcion']
                        producto.unidadmedida = f.cleaned_data['unidadmedida']
                        if f.cleaned_data['peligrosidad']:
                            producto.peligrosidad = f.cleaned_data['peligrosidad']
                    producto.save(request)
                    log(u'Editó Producto : %s' % producto, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                producto = Producto.objects.get(pk=request.POST['id'])
                producto.status=False
                producto.save(request)
                log(u'Eliminó Producto : %s' % producto, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addpeligrosidad':
            try:
                f = PeligrosidadProductoForm(request.POST)
                if f.is_valid():
                    peligrosidad = PeligrosidadProducto(
                                        descripcion=f.cleaned_data['descripcion'],
                                        )
                    peligrosidad.save(request)
                    log(u'Agregó peligrosidad de Producto : %s' % peligrosidad.descripcion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editpeligrosidad':
            try:
                peligrosidad = PeligrosidadProducto.objects.get(pk=request.POST['id'])
                f = PeligrosidadProductoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['descripcion']:
                        peligrosidad.descripcion = f.cleaned_data['descripcion']
                        peligrosidad.save(request)
                        log(u'Editó peligrosidad de Producto : %s' % peligrosidad.descripcion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletepeligrosidad':
            try:
                peligrosidad = PeligrosidadProducto.objects.get(pk=request.POST['id'])
                peligrosidad.status=False
                peligrosidad.save(request)
                log(u'Eliminó peligrosidad de Producto : %s' % peligrosidad.descripcion, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'calcularvalores':
            try:
                anio_anterior = hoy.date().year - 1
                inicio, fin = datetime(anio_anterior, 1, 1), datetime(anio_anterior, 12, 31)
                tiempo_reposicion=15
                productos_ids= KardexInventario.objects.filter(fecha__range=(inicio, fin),tipomovimiento=2, status=True).values_list('producto_id').distinct()
                for id_p in list(set(productos_ids)):
                    valores_salida = []
                    total_salida = 0
                    #CÁLCULO DE VALORES ENTRADA
                    kardexs =KardexInventario.objects.filter(fecha__range=(inicio, fin),tipomovimiento=2, producto_id=id_p[0],status=True)
                    for mes in range(1, 13):
                        ultimo_dia = calendar.monthrange(anio_anterior, mes)[1]
                        i_mes = datetime(anio_anterior, mes, 1)
                        f_mes = datetime(anio_anterior, mes, ultimo_dia)
                        kardexs_mes=kardexs.filter(fecha__range=(i_mes,f_mes)).aggregate(valor_salida=Sum('valor'),total_cantidad=Sum('cantidad'))
                        valor_salida = round(kardexs_mes['valor_salida'], 2) if kardexs_mes['valor_salida'] else 0
                        total_cantidad = round(kardexs_mes['total_cantidad'],2) if kardexs_mes['total_cantidad'] else 0
                        total_salida+=valor_salida
                        diccionario={'mes':mes,'valor_salida':valor_salida, 'total_cantidad':total_cantidad}
                        valores_salida.append(diccionario)
                    consumo_minimo = round(min(valores_salida, key=lambda x: x["valor_salida"])["valor_salida"],2)
                    consumo_maximo = round(max(valores_salida, key=lambda x: x["valor_salida"])["valor_salida"],2)
                    consumo_medio = round(statistics.mean([float(d["valor_salida"]) for d in valores_salida]),2)
                    consumo_minimo = consumo_minimo if not consumo_minimo == 0 else 1
                    cantidad_minima= min(valores_salida, key=lambda x: x["total_cantidad"])["total_cantidad"]
                    cantidad_maxima= max(valores_salida, key=lambda x: x["total_cantidad"])["total_cantidad"]
                    cantidad_minima = cantidad_minima if not cantidad_minima == 0 else 1
                    producto=Producto.objects.get(id=id_p[0])
                    producto.consumo_minimo_diario=consumo_minimo
                    producto.consumo_medio_diario=consumo_medio
                    producto.consumo_maximo_diario=consumo_maximo
                    producto.kardex_maximo=cantidad_maxima
                    producto.kardex_minimo=cantidad_minima
                    producto.tiempo_reposicion_inventario=tiempo_reposicion
                    producto.save(request)
                    producto.minimo = producto.calcular_existencia_minima()
                    producto.maximo = producto.calcular_existencia_maxima()
                    producto.save(request)
                    # totales = {'id_producto': id_p[0], 'total_salida': total_salida,
                    #            'consumo_minimo': consumo_minimo,
                    #            'consumo_maximo': consumo_maximo,
                    #            'consumo_medio': consumo_medio,
                    #            'cantidad_minima': cantidad_minima,
                    #            'cantidad_maxima': cantidad_maxima,
                    #            }
                    # print(totales)
                    log(u'Edito valores de producto : %s' % producto.descripcion, request, "edit")
                # CÁLCULO DE VALORES SALIDA
                return JsonResponse({'result': True}, safe=True)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": f"{ex}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_productos')
                    data['title'] = u'Crear Producto'
                    form = ProductoForm()
                    form.add()
                    data['form'] = form
                    return render(request, 'adm_productos/add.html', data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_productos')
                    data['title'] = u'Modificar Producto'
                    data['producto'] = producto = Producto.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(producto)
                    form = ProductoForm(initial=initial)
                    form.editar(producto)
                    data['form'] = form
                    return render(request, 'adm_productos/edit.html', data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_productos')
                    data['title'] = u'Eliminar Producto'
                    data['producto'] = Producto.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_productos/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'peligrosidad':
                try:
                    data['title'] = u'Peligrosidad'
                    search = None
                    ids = None
                    tipo = None
                    peligrosidades = PeligrosidadProducto.objects.filter(status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        peligrosidades = peligrosidades.filter(  Q(descripcion__icontains=search) )
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        peligrosidades = peligrosidades.filter(id=ids)
                    paging = MiPaginador(peligrosidades, 25)
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
                    data['peligrosidades'] = page.object_list
                    return render(request, "adm_productos/peligrosidad.html", data)

                except Exception as ex:
                    pass
            elif action == 'addpeligrosidad':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_productos')
                    data['title'] = u'Crear Peligrosidad'
                    form = PeligrosidadProductoForm()
                    data['form'] = form
                    return render(request, 'adm_productos/addpeligrosidad.html', data)
                except Exception as ex:
                    pass

            elif action == 'editpeligrosidad':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_productos')
                    data['title'] = u'Modificar peligrosidad'
                    data['peligrosidad'] = peligrosidad = PeligrosidadProducto.objects.get(pk=encrypt(request.GET['id']))
                    initial = model_to_dict(peligrosidad)
                    form = PeligrosidadProductoForm(initial=initial)
                    data['form'] = form
                    return render(request, 'adm_productos/editpeligrosidad.html', data)
                except Exception as ex:
                    pass

            elif action == 'deletepeligrosidad':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_productos')
                    data['title'] = u'Eliminar peligrosidad'
                    data['peligrosidad'] = PeligrosidadProducto.objects.get(pk=encrypt(request.GET['id']))
                    return render(request, 'adm_productos/deletepeligrosidad.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Gestión de productos'
                search = None
                ids = None
                tipo = None
                if 't' in request.GET and int(request.GET['t']) > 0:
                    data['tipoid'] = tipo = int(request.GET['t'])
                    productos = Producto.objects.filter(tipoproducto__id=tipo)
                elif 's' in request.GET:
                    search = request.GET['s']
                    productos = Producto.objects.filter(Q(codigo__icontains=search) |
                                                        Q(descripcion__icontains=search) |
                                                        Q(cuenta__descripcion__icontains=search))
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    productos = Producto.objects.filter(id=ids)
                else:
                    productos = Producto.objects.all()
                paging = MiPaginador(productos, 25)
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
                data['productos'] = page.object_list
                data['tipos_productos'] = TipoProducto.objects.all()
                return render(request, "adm_productos/productos.html", data)
            except Exception as ex:
                pass