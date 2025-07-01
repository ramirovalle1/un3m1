# -*- coding: latin-1 -*-
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
import random
import xlwt
from xlwt import *
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import InstitucionEducacionSuperiorForm, InstitucionesColegioForm,ColegioForm, TipoColegioForm, ColegioHojaVidaForm
from sga.funciones import MiPaginador, log
from sga.models import InstitucionEducacionSuperior, InstitucionesColegio, Colegio, TipoColegio
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = InstitucionesColegioForm(request.POST)
                if f.is_valid():
                    institucionescolegio = InstitucionesColegio(nombre=f.cleaned_data['nombre'],
                                                                provincia=f.cleaned_data['provincia'],
                                                                tipocolegio=f.cleaned_data['tipocolegio'],
                                                                canton=f.cleaned_data['canton']
                                                                )
                    institucionescolegio.save(request)
                    log(u'Adiciono colegio: %s' % institucionescolegio, request, "add")
                    return JsonResponse({"result": "ok", "id": institucionescolegio.id})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecolegio':
            try:
                colegio = InstitucionesColegio.objects.get(pk=request.POST['id'])
                log(u'Elimino colegio: %s' % colegio.nombre, request, "del")
                colegio.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'edit':
            try:
                institucionescolegio = InstitucionesColegio.objects.get(pk=request.POST['id'])
                f = InstitucionesColegioForm(request.POST)
                if f.is_valid():
                    institucionescolegio.nombre = f.cleaned_data['nombre']
                    institucionescolegio.provincia = f.cleaned_data['provincia']
                    institucionescolegio.canton = f.cleaned_data['canton']
                    institucionescolegio.tipocolegio = f.cleaned_data['tipocolegio']
                    institucionescolegio.save(request)
                    log(u'Modifico colegio: %s' % institucionescolegio, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcolegiohojadevida':
            try:
                colegio = Colegio.objects.get(pk=int(encrypt(request.GET['id'])))
                f = ColegioHojaVidaForm(request.POST)
                if f.is_valid():
                    colegio.nombre = f.cleaned_data['nombre']
                    colegio.codigo = f.cleaned_data['codigo']
                    colegio.canton = f.cleaned_data['canton']
                    colegio.tipo = f.cleaned_data['tipo']
                    colegio.save(request)
                    log(u'Modifico colegio de Hoja de Vida: %s' % colegio, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecolegiohojadevida':
            try:
                colegio = Colegio.objects.get(pk=int(request.POST['id']))
                log(u'Elimino : %s' % colegio.nombre, request, "del")
                colegio.status = False
                colegio.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcolegio':
            try:
                f = ColegioHojaVidaForm(request.POST)
                if f.is_valid():
                    colegio = Colegio(nombre=f.cleaned_data['nombre'],
                                      codigo=f.cleaned_data['codigo'],
                                      canton=f.cleaned_data['canton'],
                                      tipo=f.cleaned_data['tipo'])
                    colegio.save(request)
                    log(u'Adiciono colegio: %s' % colegio, request, "addcolegio")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addtipocolegio':
            try:
                f = TipoColegioForm(request.POST)
                if f.is_valid():
                    tpcolegio = TipoColegio(nombre=f.cleaned_data['nombre'], estado=f.cleaned_data['estado'])
                    tpcolegio.save(request)
                    messages.success(request, 'Se guardó exitosamente')
                    log(u'Adiciono Tipo Colegio: %s' % tpcolegio, request, "addtipocolegio")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittipocolegio':
            try:
                tiposcolegio = TipoColegio.objects.get(pk=request.POST['id'])
                f = TipoColegioForm(request.POST)
                if f.is_valid():
                    tiposcolegio.nombre = f.cleaned_data['nombre']
                    tiposcolegio.estado = f.cleaned_data['estado']
                    tiposcolegio.save(request)
                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modifico Tipo Colegio: %s' % tiposcolegio, request, "edittipocolegio")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletetipocolegio':
            try:
                tiposcolegio = TipoColegio.objects.get(pk=request.POST['id'])
                log(u'Elimino Tipo Colegio: %s' % tiposcolegio.nombre, request, "del")
                tiposcolegio.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'estadotipocolegio':
            try:
                tipo = TipoColegio.objects.get(pk=request.POST['id'])
                tipo.estado = True if request.POST['val'] == 'y' else False
                tipo.save(request)
                log(u'Estado de Tipo de Colegio actualizado : %s (%s)' % (tipo, tipo.estado),
                    request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Estado de %s actualizado." % (tipo.nombre)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

    else:
        data['title'] = u'Instituciones Colegio'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nuevo Colegio'
                    form = InstitucionesColegioForm()
                    data['form'] = form
                    return render(request, "institucionescolegio/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Colegio'
                    data['institucionescolegio'] = institucionescolegio = InstitucionesColegio.objects.get(pk=request.GET['id'])
                    form = InstitucionesColegioForm(initial={'nombre': institucionescolegio.nombre,
                                                             'provincia': institucionescolegio.provincia,
                                                             'canton': institucionescolegio.canton,
                                                             'tipocolegio': institucionescolegio.tipocolegio
                                                             })
                    form.editar(institucionescolegio)
                    data['form'] = form
                    return render(request, "institucionescolegio/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletecolegio':
                try:
                    data['title'] = u'Eliminar Colegio'
                    data['colegio'] = InstitucionesColegio.objects.get(pk=request.GET['idcolegio'])
                    return render(request, "institucionescolegio/deletecolegio.html", data)
                except Exception as ex:
                    pass

            elif action == 'colegioshojadevida':
                try:
                    data['title'] = u'Colegios'
                    search = None
                    ids = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        colegio = Colegio.objects.filter(id=ids)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        colegio = Colegio.objects.filter(Q(nombre__icontains=search)).distinct()
                    else:
                        colegio = Colegio.objects.filter(status=True).order_by('nombre')
                    numerofilas = 25
                    paging = MiPaginador(colegio, numerofilas)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        else:
                            p = paginasesion
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['numeropagina'] = p
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['colegio'] = page.object_list
                    return render(request, "institucionescolegio/colegioshojadevida.html", data)
                except Exception as ex:
                    pass


            elif action == 'editcolegiohojadevida':
                try:
                    data['title'] = u'Editar Colegio'
                    data['colegio'] = colegio = Colegio.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ColegioHojaVidaForm(initial={'nombre': colegio.nombre,'codigo': colegio.codigo,
                                                             'canton': colegio.canton,
                                                             'tipo colegio': colegio.tipo
                                                             })
                    # form.editar(colegio)
                    data['form'] = form
                    return render(request, "institucionescolegio/editcolegiohojadevida.html", data)
                except Exception as ex:
                    pass


            elif action == 'addcolegio':
                try:
                    data['title'] = u'Nuevo Colegio'
                    form = ColegioHojaVidaForm()
                    data['form'] = form
                    return render(request, "institucionescolegio/addcolegio.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewtipocolegio':
                try:
                    data['title'] = u'Listado de Tipos de Colegios'

                    search = None
                    ids = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        tiposColegios = TipoColegio.objects.filter(id=ids)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        tiposColegios = TipoColegio.objects.filter(
                            Q(nombre__icontains=search)).distinct()
                    else:
                        tiposColegios = TipoColegio.objects.filter(status=True).order_by(
                            'id')
                    numerofilas = 25
                    paging = MiPaginador(tiposColegios, numerofilas)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        else:
                            p = paginasesion
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['numeropagina'] = p
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['tiposColegios'] = page.object_list

                    return render(request, "institucionescolegio/viewTipoColegio.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipocolegio':
                try:
                    data['title'] = u'Nuevo Tipo Colegio'
                    form = TipoColegioForm()
                    data['form'] = form
                    return render(request, "institucionescolegio/addtipocolegio.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittipocolegio':
                try:
                    data['title'] = u'Editar Tipo Colegio'
                    data['tiposcolegio'] = tiposcolegio = TipoColegio.objects.get(pk=request.GET['id'])
                    form = TipoColegioForm(initial={'nombre': tiposcolegio.nombre, 'estado': tiposcolegio.estado})
                    data['form'] = form
                    return render(request, "institucionescolegio/editTipoColegio.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletetipocolegio':
                try:
                    data['title'] = u'Eliminar Tipo Colegio'
                    data['tiposcolegio'] = TipoColegio.objects.get(pk=request.GET['idtipocolegio'])
                    return render(request, "institucionescolegio/deletetipocolegio.html", data)
                except Exception as ex:
                    pass

            elif action == 'excelcolegios':
                try:
                    __author__ = 'Unemi'
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Listas_Colegios' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"NOMBRE", 10000),
                        (u"PROVINCIA", 5000),
                        (u"CANTON", 5000),
                        (u"TIPO COLEGIO", 3500),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listacolegios = InstitucionesColegio.objects.filter(status=True).order_by('nombre')
                    row_num = 4
                    for libros in listacolegios:
                        i = 0
                        campo1 = libros.nombre
                        campo2 = libros.provincia.nombre
                        campo3 = libros.canton.nombre
                        campo4 = libros.tipocolegio.nombre

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'viewcolegiohojadevida':
                try:
                    querybase = Colegio.objects.all().order_by('-id')
                    search = request.GET.get('search', '')
                    filtros = Q(status=True)
                    url_vars = ''
                    if search:
                        data['search'] = search
                        s = search.split()
                        url_vars += "&search={}".format(search)
                        filtros = filtros & (Q(nombre__icontains=search) | Q(codigo__icontains=search))
                    data['url_vars'] = url_vars
                    colegio = querybase.filter(filtros)
                    numerofilas = 25
                    paging = MiPaginador(colegio, numerofilas)
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
                    data['search'] = search if search else ""
                    data['colegios'] = page.object_list
                    return render(request, "institucionescolegio/viewcolegioprincipal.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 'id' in request.GET:
                ids = request.GET['id']
                institucioneducacionsuperior = InstitucionesColegio.objects.filter(id=ids)
            elif 's' in request.GET:
                search = request.GET['s']
                institucioneducacionsuperior = InstitucionesColegio.objects.filter(Q(nombre__icontains=search)).distinct()
            else:
                institucioneducacionsuperior = InstitucionesColegio.objects.filter(status=True).order_by('nombre')
            numerofilas = 25
            paging = MiPaginador(institucioneducacionsuperior, numerofilas)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                    if p == 1:
                        numerofilasguiente = numerofilas
                    else:
                        numerofilasguiente = numerofilas * (p - 1)
                else:
                    p = paginasesion
                    if p == 1:
                        numerofilasguiente = numerofilas
                    else:
                        numerofilasguiente = numerofilas * (p - 1)
                try:
                    page = paging.page(p)
                except:
                    p = 1
                page = paging.page(p)
            except:
                page = paging.page(p)
            request.session['paginador'] = p
            data['paging'] = paging
            data['numerofilasguiente'] = numerofilasguiente
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['numeropagina'] = p
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['institucionescolegios'] = page.object_list
            return render(request, "institucionescolegio/view.html", data)
