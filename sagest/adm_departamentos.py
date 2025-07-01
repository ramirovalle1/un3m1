# -*- coding: UTF-8 -*-
import random
import sys

import xlsxwriter
import io
from django.contrib.auth.decorators import login_required
from django.core.checks import messages
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import DepartamentoForm, IntegranteDepartamentoForm, ResponsableDepartamentoForm, \
    SeccionDepartamentoForm, ProductoServicioSeccionForm, DepartamentoProductosTHForm, ImportaProductosDirForm
from sagest.funciones import encrypt_id
from sagest.models import Departamento, SeccionDepartamento, ProductoServicioSeccion, ProductoServicioTh
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import Administrativo, ModuloGrupo, Persona
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'adicionarproductos':
            try:
                seccion = SeccionDepartamento.objects.get(id=int(request.POST['id']))
                adicionalesids = request.POST['ids'].split(',')
                for a in adicionalesids:
                    producto = ProductoServicioTh.objects.get(pk=a)
                    proth = ProductoServicioSeccion(producto=producto, seccion=seccion, activo=True)
                    proth.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addproductos':
            try:
                f = DepartamentoProductosTHForm(request.POST)
                if f.is_valid():
                    factor = ProductoServicioTh(nombre=f.cleaned_data['nombre'], tipo=f.cleaned_data['tipo'], fechavigencia=f.cleaned_data['fechavigencia'])
                    factor.save(request)
                    log(u'adiciono producto th: %s' % factor, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editproductos':
            try:
                factor = ProductoServicioTh.objects.get(pk=request.POST['id'])
                f = DepartamentoProductosTHForm(request.POST)
                if f.is_valid():
                    factor.nombre = f.cleaned_data['nombre']
                    factor.tipo = f.cleaned_data['tipo']
                    factor.fechavigencia = f.cleaned_data['fechavigencia']
                    factor.save(request)
                    log(u'edito producto th: %s' % factor, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteproductos':
            try:
                factor = ProductoServicioTh.objects.get(pk=request.POST['id'])
                factor.status = False
                factor.save(request)
                log(u'Elimino Producto th: %s' % factor, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'mostrarproducto':
            try:
                evento = ProductoServicioSeccion.objects.get(pk=request.POST['id'])
                evento.activo = True if request.POST['val'] == 'y' else False
                evento.save(request)
                log(u'Visualiza Producto en Getion: %s (%s)' % (evento, evento.activo),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'delproductoseccion':
            try:
                factor = ProductoServicioSeccion.objects.get(pk=request.POST['id'])
                log(u'Elimino Producto th: %s' % factor, request, "edit")
                factor.delete()
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        if action == 'adddepartamento':
            try:
                f = DepartamentoForm(request.POST)
                if not f.is_valid():
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                departamento = Departamento(nombre=f.cleaned_data['nombre'],
                                            grupodepartamento=f.cleaned_data['grupodepartamento'],
                                            permisogeneral=f.cleaned_data['permisogeneral'],
                                            codigoindice=f.cleaned_data['codigoindice'],
                                            permisodepartamento=f.cleaned_data['permisodepartamento'],
                                            tipoindice=f.cleaned_data['tipoindice'])
                departamento.save(request)
                log(u'Adiciono nuevo departamento: %s' % departamento, request, "add")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result":True, "mensaje": u"Error: %s" % ex})

        if action == 'addintegrante':
            try:
                f = IntegranteDepartamentoForm(request.POST)
                if f.is_valid():
                    departamento = Departamento.objects.get(pk=int(request.POST['idp']))
                    administrativo = Administrativo.objects.get(pk=int(request.POST['id']))
                    departamento.integrantes.add(administrativo.persona)
                    log(u'Adiciono nuevo integrante al departamento: %s' % departamento, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                departamento = Departamento.objects.get(pk=encrypt_id(request.POST['id']))
                f = DepartamentoForm(request.POST, instancia=departamento)
                f.fields['nombre'].required = False
                if not f.is_valid():
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                departamento.grupodepartamento = f.cleaned_data['grupodepartamento']
                # departamento.nombre = f.cleaned_data['nombre']
                departamento.permisogeneral = f.cleaned_data['permisogeneral']
                departamento.codigoindice = f.cleaned_data['codigoindice']
                departamento.permisodepartamento = f.cleaned_data['permisodepartamento']
                departamento.tipoindice = f.cleaned_data['tipoindice']
                departamento.save(request)
                log(u'Modificó departamento: %s' % departamento, request, "edit")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error:{ex}"})

        if action == 'addresponsable':
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'])
                f = ResponsableDepartamentoForm(request.POST)
                if f.is_valid():
                    departamento.responsable = f.cleaned_data['responsable']
                    departamento.responsable_subrogante.clear()
                    for res in f.cleaned_data['responsable_subrogante']:
                        departamento.responsable_subrogante.add(res)
                    #departamento.responsable_subrogante = f.cleaned_data['responsable_subrogante']
                    departamento.save(request)
                    log(u'Modificó responsable de departamento: %s' % departamento, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addsecciones':
            try:
                f = SeccionDepartamentoForm(request.POST)
                if f.is_valid():
                    departamento = Departamento.objects.get(pk=int(request.POST['id']))
                    seccion = SeccionDepartamento(departamento=departamento,
                                                  descripcion=f.cleaned_data['descripcion'],
                                                  responsable_id=None if f.cleaned_data['responsable']  == 0 else f.cleaned_data['responsable'],
                                                  responsablesubrogante_id= None if f.cleaned_data['responsablesubrogante'] == 0 else f.cleaned_data['responsablesubrogante'],
                                                  observacion=f.cleaned_data['observacion'],
                                                  codigoindice=f.cleaned_data['codigoindice']
                                                  )
                    seccion.save(request)
                    log(u'Adiciono una nueva sección al departamento: %s' % departamento, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar, Revisa datos incompletos o Seccion duplicada."})


        if action == 'editsecciones':
            try:
                seccion = SeccionDepartamento.objects.get(pk=request.POST['id'])
                f = SeccionDepartamentoForm(request.POST)
                if f.is_valid():
                    seccion.descripcion = f.cleaned_data['descripcion']
                    seccion.responsable_id = f.cleaned_data['responsable']
                    seccion.responsablesubrogante_id = f.cleaned_data['responsablesubrogante']
                    seccion.observacion = f.cleaned_data['observacion']
                    seccion.codigoindice = f.cleaned_data['codigoindice']
                    seccion.save(request)
                    data = seccion.departamento_id
                    log(u'Modificó departamento: %s' % seccion, request, "edit")
                    return JsonResponse({"result": "ok",'id':data})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deldepartamento':
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'])
                log(u'Eliminó Departamento: %s' % Departamento, request, "del")
                departamento.status=False
                departamento.save(request,update_fields=["status"])
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        if action == 'delintegrante':
            try:
                departamento = Departamento.objects.get(pk=int(request.POST['idp']))
                administrativo = Persona.objects.get(pk=int(request.POST['id']))
                departamento.integrantes.remove(administrativo)
                log(u'Eliminó Integrante: %s' % Departamento, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'importaproducto':
            try:
                f = ImportaProductosDirForm(request.POST)
                if f.is_valid():
                    unidad = f.cleaned_data['unidad']
                    original = Departamento.objects.get(id=int(encrypt(request.POST['id'])))
                    for secc in unidad.gestiones():
                        if not SeccionDepartamento.objects.filter(departamento=original,descripcion=secc.descripcion,status=True).exists():
                            seccionsi=SeccionDepartamento(departamento = original,
                                                          descripcion = secc.descripcion,
                                                          responsable=secc.responsable,
                                                          responsablesubrogante=secc.responsablesubrogante,
                                                          codigoindice=secc.codigoindice,
                                                          activo=secc.activo)
                            seccionsi.save(request)
                            productos = secc.productoservicioseccion_set.filter(status=True)
                            for prod in productos:
                                if not ProductoServicioSeccion.objects.filter(producto=prod.producto,
                                                                              seccion=seccionsi,
                                                                              activo=True).exists():
                                    producto = ProductoServicioSeccion(producto=prod.producto,
                                                            seccion=seccionsi, activo=True)
                                    producto.save()

                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delseccion':
            try:
                seccion = SeccionDepartamento.objects.get(pk=int(request.POST['id']))
                seccion.delete()
                log(u'Eliminó gestión: %s' % seccion, request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        if action == 'cambiarseccion':
            try:
                seccion = SeccionDepartamento.objects.get(pk=request.POST['id'])
                seccion.activo = True if request.POST['val'] == 'y' else False
                seccion.save(request)
                log(u'Cambia estado de activo a sección %s: %s' % (seccion, seccion.activo),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'cambiarseccionactividad':
            try:
                seccion = SeccionDepartamento.objects.get(pk=request.POST['id'])
                seccion.noactividades = True if request.POST['val'] == 'y' else False
                seccion.save(request)
                log(u'Cambia estado de actividad a sección %s: %s' % (seccion, seccion.activo),request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'cambiaractividad':
            try:
                direccion = Departamento.objects.get(pk=request.POST['id'])
                direccion.noactividades = True if request.POST['val'] == 'y' else False
                direccion.save(request)
                log(u'Ingresa actividades dirección en plantilla : %s (%s)' % (direccion, direccion.noactividades),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'cambiarmostrar':
            try:
                direccion = Departamento.objects.get(pk=request.POST['id'])
                direccion.visualizath = True if request.POST['val'] == 'y' else False
                direccion.save(request)
                log(u'Visualiza dirección en plantilla : %s (%s)' % (direccion, direccion.visualizath),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'cambiaractivo':
            try:
                producto = ProductoServicioSeccion.objects.get(pk=request.POST['id'])
                producto.activo = True if request.POST['val'] == 'y' else False
                producto.save(request,update_fields=["activo"])
                log(u'Cambia estado de visibile : %s (%s)' % (producto, producto.activo),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'adddepartamento':
                try:
                    data['form'] = DepartamentoForm()
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error_{ex}'})

            if action == 'editsecciones':
                try:
                    data['title'] = u'Editar gestión'
                    data['seccion'] = request.GET['ids']
                    data['gestion'] = gestion = SeccionDepartamento.objects.get(pk=int(request.GET['id']))
                    form = SeccionDepartamentoForm(initial={'descripcion': gestion.descripcion,
                                                            'observacion': gestion.observacion,
                                                            'responsable': gestion.responsable,
                                                            'responsablesubrogante': gestion.responsablesubrogante,
                                                            'codigoindice': gestion.codigoindice
                                                            })
                    data['form'] = form
                    return render(request, "adm_departamentos/editsecciones.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['departamento'] = departamento = Departamento.objects.get(pk=int(request.GET['id']))
                    form = DepartamentoForm(initial=model_to_dict(departamento))
                    form.editar()
                    data['id'] = departamento.id
                    data['switchery'] = True
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error_{ex}'})

            if action == 'reportesxlsdepint':
                try:
                    departamentos = Departamento.objects.filter(status=True).order_by('nombre')
                    departamentos = departamentos.filter(integrantes__isnull=False).distinct()


                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_column(0, 100, 60)

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})

                    ws.write(0, 0, 'DEPARTAMENTO', formatoceldagris)
                    ws.write(0, 1, 'INTEGRANTES', formatoceldagris)

                    fila = 1
                    enca = fila
                    for dep in departamentos:
                        departamento = dep.nombre
                        resp = dep.responsable
                        resp_subrogante = dep.responsable_subrogante.all()
                        personal = dep.integrantes.all()


                        ws.write(fila, 0, str(departamento), formatoceldaleft)

                        for per in personal:
                            ws.write(fila, 1, str(per), formatoceldaleft)
                            fila += 1
                        fila +=1
                    workbook.close()
                    output.seek(0)
                    filename = 'plantilla_%s.xlsx'  # % (contra.contrato.regimenlaboral)
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportesxls':
                try:
                    departamentos = Departamento.objects.filter(status=True).order_by('nombre')
                    departamentos = departamentos.filter(integrantes__isnull=False).distinct()


                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_column(0, 100, 60)

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})

                    ws.write(0, 0, 'DEPARTAMENTO', formatoceldagris)
                    ws.write(0, 1, 'REPONSABLE', formatoceldagris)
                    ws.write(0, 2, 'CARGO', formatoceldagris)
                    ws.write(0, 3, 'RESP. SUBROGANTE', formatoceldagris)
                    ws.write(0, 4, 'CARGO', formatoceldagris)
                    ws.write(0, 5, 'INTEGRANTES', formatoceldagris)
                    ws.write(0, 6, 'CARGO', formatoceldagris)
                    ws.write(0, 7, 'NUM. INTEGRANTES', formatoceldagris)
                    cont = 6
                    fila = 1
                    enca = fila
                    for dep in departamentos:
                        departamento = dep.nombre
                        responsable = dep.responsable
                        cargos = dep.responsable.cargo_persona()
                        respsubrogante = dep.responsable_subrogante.all()
                        integrantes = dep.cantidad_integrantes()
                        personal = dep.integrantes.all()
                        cargos_sub = []
                        cargos_personal =[]
                        for ca in respsubrogante:
                            if ca.cargo_persona_2():
                                carg = ca.cargo_persona_2()
                                cargos_sub.append(carg)
                            else:
                                cargos_sub.append("")
                        for per in personal:
                            if per.cargo_persona_2():
                                pers = per.cargo_persona_2()
                                cargos_personal.append(pers)
                            else:
                                cargos_personal.append("")


                        ws.write(fila, 0,str(departamento), formatoceldaleft)
                        ws.write(fila, 1, str(responsable), formatoceldaleft)
                        ws.write(fila, 2, str(cargos), formatoceldaleft)
                        ws.write(fila, 7, str(integrantes), formatoceldaleft)
                        for sub, car in zip(respsubrogante, cargos_sub):
                            fila +=1
                            ws.write(fila, 3, str(sub), formatoceldaleft)
                            ws.write(fila, 4, str(car), formatoceldaleft)
                        for per, car_per in zip(personal, cargos_personal):
                            enca +=1
                            ws.write(enca, 5, str(per), formatoceldaleft)
                            ws.write(enca, 6, str(car_per), formatoceldaleft)


                        enca +=1
                        fila =enca
                    workbook.close()
                    output.seek(0)
                    filename = 'plantilla_%s.xlsx'  # % (contra.contrato.regimenlaboral)
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response

                except Exception as ex:
                    pass

            elif action == 'addintegrante':
                try:
                    data['title'] = u'Adicionar integrante'
                    data['form'] = IntegranteDepartamentoForm()
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['idp']))
                    return render(request, "adm_departamentos/addintegrante.html", data)
                except Exception as ex:
                    pass

            elif action == 'addresponsable':
                try:
                    data['title'] = u'Establecer responsable'
                    data['departamento'] = departamento = Departamento.objects.get(pk=int(request.GET['id']))
                    form = ResponsableDepartamentoForm(initial=model_to_dict(departamento))
                    form.fields['responsable_subrogante'].queryset = Persona.objects.filter(status=True, id__in=departamento.integrantes.all().values_list('pk', flat=True))
                    data['form'] = form
                    return render(request, "adm_departamentos/addresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsecciones':
                try:
                    data['title'] = u'Adicionar secciones'
                    data['departamento'] = departamento = Departamento.objects.get(pk=int(request.GET['id']))
                    data['form'] = SeccionDepartamentoForm()
                    return render(request, "adm_departamentos/addsecciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'editseccion':
                try:
                    data['title'] = u'Editar Gestión'
                    data['gestion'] = gestion = SeccionDepartamento.objects.get(pk=int(request.GET['id']))

                    form = SeccionDepartamentoForm(initial={'descripcion': gestion.descripcion,
                                                     'observacion': gestion.observacion,
                                                     'responsable': gestion.responsable,
                                                     'responsablesubrogante':gestion.responsablesubrogante
                                                            })
                    data['form'] = form
                    return render(request, "adm_departamentos/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'listaproductos':
                try:
                    usados = ProductoServicioSeccion.objects.values_list('producto_id', flat=True).filter(seccion_id = request.GET['seccion'])
                    lista = []
                    for p in ProductoServicioTh.objects.filter(status=True).exclude(pk__in=usados):
                        lista.append([p.id, p.nombre])
                    return JsonResponse({'result': 'ok', 'productos': lista})
                except Exception as ex:
                    transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'addproductosgestion':
                try:
                    usados = ProductoServicioSeccion.objects.values_list('producto_id', flat=True).filter(seccion_id=request.GET['id'])
                    data['gestion'] = SeccionDepartamento.objects.get(pk=request.GET['id'])
                    data['productos'] = ProductoServicioTh.objects.filter(status=True).exclude(pk__in=usados)
                    template = get_template('adm_departamentos/productosgestion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'importaproducto':
                try:
                    data['id'] = int(request.GET['id'])
                    form = ImportaProductosDirForm()
                    form.con_producto()
                    data['form'] = form
                    data['action'] = action
                    template = get_template("adm_departamentos/modal/importarprod.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            elif action == 'buscarproducto':
                try:
                    unidad = request.GET['unidad']
                    servicios = ProductoServicioSeccion.objects.filter(status=True,seccion__departamento_id=int(unidad))
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x)}
                                        for x in servicios]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass


            if action == 'integrantes':
                try:
                    data['title'] = u'Adicionar integrantes'
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_departamentos/integrantes.html", data)
                except Exception as ex:
                    pass

            if action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s) == 1:
                        per = Persona.objects.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(
                                                         apellido2__icontains=q) | Q(cedula__contains=q)),
                                                     Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = Persona.objects.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         nombres__icontains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         apellido1__contains=s[1]))).filter(status=True).distinct()[
                              :15]
                    else:
                        per = Persona.objects.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(
                                                         apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(
                                                         nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(
                            status=True).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass
            if action == 'secciones':
                try:
                    data['title'] = u'Secciones del departamento'
                    data['departamento'] = departamento = Departamento.objects.get(pk=int(request.GET['id']))
                    data['secciones'] = departamento.secciondepartamento_set.filter(status=True)
                    return render(request, "adm_departamentos/secciones.html", data)
                except Exception as ex:
                    pass

            if action == 'viewproductos':
                try:
                    data['title'] = u'Productos y servicios'
                    data['seccion'] = gestion = SeccionDepartamento.objects.get(pk=int(request.GET['id']))
                    data['productos'] = gestion.productoservicioseccion_set.filter(status=True).order_by('id')
                    return render(request, "adm_departamentos/viewproductos.html", data)
                except Exception as ex:
                    pass

            if action == 'productos':
                try:
                    data['title'] = u'Productos o Servicios'
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        factores = ProductoServicioTh.objects.filter(nombre__icontains=search, status=True).order_by('-id')
                    else:
                        factores = ProductoServicioTh.objects.filter(status=True).order_by('-id')
                    paging = MiPaginador(factores, 25)
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
                    data['factores'] = page.object_list
                    return render(request, "adm_departamentos/productos.html", data)
                except Exception as ex:
                    pass

            if action == 'addproductos':
                try:
                    data['title'] = u'Adicionar Producto o Servicio'
                    data['form'] = DepartamentoProductosTHForm()
                    return render(request, 'adm_departamentos/addproducto.html', data)
                except Exception as ex:
                    pass

            if action == 'editproductos':
                try:
                    data['title'] = u'Modificar Producto o Servicio'
                    data['dicom'] = filtro = ProductoServicioTh.objects.get(pk=request.GET['id'])
                    data['form'] = DepartamentoProductosTHForm(initial=model_to_dict(filtro))
                    return render(request, 'adm_departamentos/editproducto.html', data)
                except Exception as ex:
                    pass

            if action == 'deleteproductos':
                try:
                    data['title'] = u'Eliminar Producto o Servicio'
                    data['diccionario'] = ProductoServicioTh.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_departamentos/deleteproducto.html', data)
                except Exception as ex:
                    pass


            if action == 'registro_opciones':
                try:
                    __author__ = 'Unemi'
                    departamento = Departamento.objects.get(pk=int(request.GET['id']))
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Matriz_opciones' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"NUM", 2000),
                        (u"EMPLEADO", 10000),
                        (u"ESTADO", 10000),
                        (u"CARGO", 10000),
                        (u"MODULO", 10000),
                        (u"OPCIÓN", 10000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 4
                    i = 0
                    for integrante in departamento.mis_integrantes():
                        campo1 = integrante.nombre_completo_inverso()
                        distributivo = integrante.mis_cargos_departamento(departamento)[0]
                        campo2 = distributivo.estadopuesto.descripcion
                        cargo =  distributivo.denominacionpuesto.descripcion
                        campo3 = cargo
                        ws.write(row_num, 0, i+1, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        bandera = 0
                        for grupo in integrante.grupos():
                            bandera = 1
                            ws.write(row_num, 4, grupo.name, font_style2)
                            # modulos
                            bandera2 = 0
                            for md in ModuloGrupo.objects.filter(grupos=grupo, status=True)[0].modulos_activos():
                                bandera2 = 1
                                ws.write(row_num, 5, md.descripcion, font_style2)
                                row_num += 1
                            if bandera2 == 0:
                                row_num += 1
                            row_num += 1

                        if bandera == 0:
                            row_num += 1
                        i += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Departamentos de la institución'
                search = None
                ids = None
                tipob = 2
                departamentos = Departamento.objects.filter(status=True).order_by('nombre')
                if 'tipo' in request.GET:
                    tipob = int(request.GET['tipo'])
                if tipob == 2:
                        departamentos = departamentos.filter(integrantes__isnull=False).distinct()
                elif tipob == 3:
                        departamentos = departamentos.filter(integrantes__isnull=True).distinct()
                if 's' in request.GET:
                    search = request.GET['s']
                    departamentos = departamentos.filter(nombre__unaccent__icontains=search)
                if 'id' in request.GET:
                    ids = request.GET['id']
                    departamentos = departamentos.filter(id=ids)
                paging = MiPaginador(departamentos, 20)
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
                data['tipob'] =tipob
                data['departamentos'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, 'adm_departamentos/view.html', data)
            except Exception as ex:
                pass