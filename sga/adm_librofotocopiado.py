# -*- coding: UTF-8 -*-
import random
import xlwt
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import LibroFotocopiadoForm
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import LibroKohaProgramaAnaliticoAsignatura, LibroFotocopiado
from sga.templatetags.sga_extras import encrypt

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

        if action == 'add':
            try:
                f = LibroFotocopiadoForm(request.POST)
                arch = request.FILES['archivo']
                extencion = arch._name.split('.')
                exte = extencion[1]
                if arch.size > 15728640:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 15 Mb."})
                if not exte == 'pdf':
                    return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                if f.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("Libro_", newfile._name)
                        libro = LibroFotocopiado(codigokoha=f.cleaned_data['codigokoha'],
                                                  nombre=f.cleaned_data['nombre'],
                                                  autor=f.cleaned_data['autor'],
                                                  aniopublicacion=f.cleaned_data['aniopublicacion'],
                                                  editorial=f.cleaned_data['editorial'],
                                                  ciudad=f.cleaned_data['ciudad'],
                                                  archivo=newfile)
                        libro.save(request)
                        log(u'Adicionó nuevo libro fotocopiado: %s' % libro, request,"add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                f = LibroFotocopiadoForm(request.POST)
                newfile = None
                libros = LibroFotocopiado.objects.get(pk=int(encrypt(request.POST['id'])))
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 15728640:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 15 Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                if f.is_valid():
                    libros.codigokoha = f.cleaned_data['codigokoha']
                    libros.nombre = f.cleaned_data['nombre']
                    libros.autor = f.cleaned_data['autor']
                    libros.aniopublicacion = f.cleaned_data['aniopublicacion']
                    libros.editorial = f.cleaned_data['editorial']
                    libros.ciudad = f.cleaned_data['ciudad']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("Libro_", newfile._name)
                        libros.archivo = newfile
                    libros.save(request)
                    log(u'Editó libro de biblioteca: %s' % libros, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                libro = LibroFotocopiado.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó el libro fotocopiado: %s' % libro, request, "del")
                libro.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Libro Fotocopiado'
                    form =LibroFotocopiadoForm()
                    data['form'] = form
                    return render(request, 'adm_librofotocopiado/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar Libro Fotocopiado'
                    data['libro'] = libro = LibroFotocopiado.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = LibroFotocopiadoForm(initial={'codigokoha': libro.codigokoha,
                                                        'nombre': libro.nombre,
                                                        'autor': libro.autor,
                                                        'aniopublicacion': libro.aniopublicacion,
                                                        'editorial': libro.editorial,
                                                        'ciudad': libro.ciudad})
                    data['form'] = form
                    return render(request, "adm_librofotocopiado/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Libro Fotocopiado'
                    data['libro'] = LibroFotocopiado.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_librofotocopiado/delete.html", data)
                except Exception as ex:
                    pass

            if action == 'excelibrosbibliotecas':
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
                        'Content-Disposition'] = 'attachment; filename=Listas_Libros' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CODIGO KOHA", 2500),
                        (u"NOMBRE LIBRO", 4500),
                        (u"AUTOR", 2000),
                        (u"PUBLICACION", 2000),
                        (u"EDITORIAL", 10000),
                        (u"CANTIDAD", 10000),
                        (u"CIUDAD", 3000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listalibros = LibroKohaProgramaAnaliticoAsignatura.objects.filter(status=True).order_by('nombre')
                    row_num = 4
                    for libros in listalibros:
                        i = 0
                        campo1 = libros.codigokoha
                        campo2 = libros.nombre
                        campo3 = libros.autor
                        campo4 = libros.aniopublicacion
                        campo5 = libros.editorial
                        campo6 = libros.cantidad
                        campo7 = libros.ciudad

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de libros fotocopiados'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    librosinvestigacion = LibroFotocopiado.objects.filter((Q(nombre__icontains=search)| Q(autor__icontains=search)| Q(editorial__icontains=search)),status=True).order_by('nombre')
                else:
                    librosinvestigacion = LibroFotocopiado.objects.filter((Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1])) | (Q(autor__icontains=ss[0]) & Q(autor__icontains=ss[1])) | ((Q(editorial__icontains=ss[0]) & Q(editorial__icontains=ss[1]))), status=True).order_by('nombre')
            elif 'id' in request.GET:
                ids = request.GET['id']
                librosinvestigacion = LibroFotocopiado.objects.filter(status=True, pk=int(request.GET['id']))
            else:
                librosinvestigacion = LibroFotocopiado.objects.filter(status=True).order_by('nombre')
            paging = MiPaginador(librosinvestigacion, 25)
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
            data['librosfotocopiados'] = page.object_list
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            return render(request, "adm_librofotocopiado/view.html", data)



