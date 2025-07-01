# -*- coding: UTF-8 -*-
import random

from datetime import datetime

from django.db.models import Count
from django.template.loader import get_template
import xlwt
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context

from decorators import secure_module, last_access
from sagest.models import SolicitudPublicacion
from sga.commonviews import adduserdata
from sga.forms import EvidenciaForm, LibroInvestigacionForm, \
    ParticipanteProfesorLibroForm, ParticipanteAdministrativoLibroForm, CapituloLibroInvestigacionForm, \
    ParticipanteProfesorCapituloLibroForm, ParticipanteAdministrativoCapituloLibroForm, \
    ParticipanteProfesorPonenciaForm, LibroBibliotecaForm
from sga.funciones import MiPaginador, log, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Evidencia, DetalleEvidencias, TIPO_PARTICIPANTE_INSTITUCION, TIPO_PARTICIPANTE, \
    LibroInvestigacion, ParticipanteLibros, CapituloLibroInvestigacion, \
    ParticipanteCapituloLibros, LibroKohaProgramaAnaliticoAsignatura, SolicitudCompraLibro, Malla, AsignaturaMalla, \
    ProgramaAnaliticoAsignatura, BibliografiaProgramaAnaliticoAsignatura, DetalleSilaboSemanalBibliografiaDocente, \
    Materia, Carrera, Coordinacion, VisitasBiblioteca, DetalleSilaboSemanalBibliografia, SilaboSemanal, ProfesorMateria, \
    Silabo, Periodo
from sga.templatetags.sga_extras import encrypt



@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addlibro':
            try:
                f = LibroBibliotecaForm(request.POST)
                if f.is_valid():
                    # if not LibroKohaProgramaAnaliticoAsignatura.objects.filter(codigokoha=f.cleaned_data['codigokoha'],status=True).exists():
                    libros = LibroKohaProgramaAnaliticoAsignatura(codigokoha=f.cleaned_data['codigokoha'],
                                                                  codigoisbn=f.cleaned_data['codigoisbn'],
                                                                  nombre=f.cleaned_data['nombre'],
                                                                  titulo=f.cleaned_data['titulo'],
                                                                  autor=f.cleaned_data['autor'],
                                                                  aniopublicacion=f.cleaned_data['aniopublicacion'],
                                                                  editorial=f.cleaned_data['editorial'],
                                                                  cantidad=f.cleaned_data['cantidad'],
                                                                  idioma=f.cleaned_data['idioma'],
                                                                  ciudad=f.cleaned_data['ciudad'],
                                                                  tipo=f.cleaned_data['tipo'],
                                                                  carrera_id= request.POST['carrera'],
                                                                  hilera=f.cleaned_data['hilera'],
                                                                  areaconocimiento=f.cleaned_data['areaconocimiento'],
                                                                  subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                                                  subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                                                  url_odilo=f.cleaned_data['url_odilo'],
                                                                  )
                    libros.save(request)
                    log(u'Adicionó libro de biblioteca: %s' % libros, request,"add")
                    return JsonResponse({"result": "ok"})
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya el Libro esta ingresado."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editarlibro':
            try:
                f = LibroBibliotecaForm(request.POST)
                libros = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    libros.codigokoha = f.cleaned_data['codigokoha']
                    libros.codigoisbn = f.cleaned_data['codigoisbn']
                    libros.titulo = f.cleaned_data['titulo']
                    libros.nombre = f.cleaned_data['nombre']
                    libros.autor = f.cleaned_data['autor']
                    libros.aniopublicacion = f.cleaned_data['aniopublicacion']
                    libros.editorial = f.cleaned_data['editorial']
                    libros.cantidad = f.cleaned_data['cantidad']
                    libros.idioma = f.cleaned_data['idioma']
                    libros.ciudad = f.cleaned_data['ciudad']
                    libros.tipo = f.cleaned_data['tipo']
                    libros.carrera_id = request.POST['carrera']
                    libros.hilera = f.cleaned_data['hilera']
                    libros.areaconocimiento = f.cleaned_data['areaconocimiento']
                    libros.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                    libros.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                    libros.url_odilo = f.cleaned_data['url_odilo']
                    libros.save(request)
                    log(u'Editó libro de biblioteca: %s' % libros, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletelibro':
            try:
                libro = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk=request.POST['id'])
                log(u'Elimino libro biblioteca: %s' % libro.nombre, request, "del")
                libro.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'carreras':
            try:
                if 'id' in request.POST:
                    coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                    lista =[]
                    for car in coordinacion.carreras():
                        lista.append([car.id, car.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addlibro':
                try:
                    data['title'] = u'Adicionar Libros'
                    form =LibroBibliotecaForm()
                    form.fields['carrera'].queryset = Carrera.objects.filter(pk=None)
                    data['form'] = form
                    return render(request, 'librosbiblioteca/addlibro.html', data)
                except Exception as ex:
                    pass

            if action == 'editarlibro':
                try:
                    data['title'] = u'Editar Libro'
                    data['libros'] = libros = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk=request.GET['id'])
                    if libros.areaconocimiento:
                        nomareaconocimiento=libros.areaconocimiento
                        nomsubareaconocimiento=libros.subareaconocimiento
                        nomsubareaespecificaconocimiento=libros.subareaespecificaconocimiento
                    else:
                        nomareaconocimiento = None
                        nomsubareaconocimiento = None
                        nomsubareaespecificaconocimiento = None
                    form = LibroBibliotecaForm(initial={'codigokoha': libros.codigokoha,
                                                        'codigoisbn': libros.codigoisbn,
                                                        'titulo': libros.titulo,
                                                        'nombre': libros.nombre,
                                                        'autor': libros.autor,
                                                        'aniopublicacion': libros.aniopublicacion,
                                                        'editorial': libros.editorial,
                                                        'cantidad': libros.cantidad,
                                                        'idioma': libros.idioma,
                                                        'ciudad': libros.ciudad,
                                                        'tipo': libros.tipo,
                                                        'coordinacion': libros.carrera.coordinacion_set.filter(status=True)[0] if libros.carrera else None,
                                                        'carrera': libros.carrera,
                                                        'hilera': libros.hilera,
                                                        'areaconocimiento': nomareaconocimiento,
                                                        'url_odilo': libros.url_odilo,
                                                        'subareaconocimiento': nomsubareaconocimiento,
                                                        'subareaespecificaconocimiento': nomsubareaespecificaconocimiento })
                    if libros.carrera:
                        coordinacion = libros.carrera.coordinacion_set.filter(status=True)[0]
                        form.fields['carrera'].queryset = coordinacion.carreras()
                    else:
                        form.fields['carrera'].queryset = Carrera.objects.filter(pk=None)
                    if libros.areaconocimiento:
                        form.editar(libros)
                    data['form'] = form
                    return render(request, "librosbiblioteca/editarlibro.html", data)
                except Exception as ex:
                    pass

            if action == 'deletelibro':
                try:
                    data['title'] = u'Eliminar Libro'
                    data['libro'] = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk=request.GET['idlibro'])
                    return render(request, "librosbiblioteca/deletelibro.html", data)
                except Exception as ex:
                    pass

            if action == 'excelibrosbibliotecas':
                try:
                    __author__ = 'Unemi'
                    styrowD = easyxf( 'font: name Times New Roman, color-index black, bold off; borders: left thin, right thin, top thin, bottom thin')
                    styrow = easyxf('font: name Times New Roman, color-index black, bold off; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style_col = easyxf('font: name Times New Roman, color-index black, bold on; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    title = easyxf('font: name Times New Roman, color-index green, bold on , height 350; alignment: horiz centre')

                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listas_Libros')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Listas_Libros' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CODIGO KOHA", 2600),
                        (u"NOMBRE LIBRO", 10000),
                        (u"AUTOR", 5000),
                        (u"PUBLICACION", 3000),
                        (u"EDITORIAL", 10000),
                        (u"CANTIDAD", 3000),
                        (u"CIUDAD", 5000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], style_col)
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

                        ws.write(row_num, 0, campo1, styrow)
                        ws.write(row_num, 1, campo2.upper(), styrowD)
                        ws.write(row_num, 2, campo3.upper(), styrowD)
                        ws.write(row_num, 3, campo4, styrow)
                        ws.write(row_num, 4, campo5.upper(), styrowD)
                        ws.write(row_num, 5, campo6, styrow)
                        ws.write(row_num, 6, campo7.upper(), styrow)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'detalle_libro':
                try:
                    data['libro'] = libro = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk=int(request.GET['id']))
                    listaasignaturamalla_programa = BibliografiaProgramaAnaliticoAsignatura.objects.values_list("programaanaliticoasignatura__asignaturamalla_id", flat=False).filter(librokohaprogramaanaliticoasignatura=libro).distinct("programaanaliticoasignatura__asignaturamalla")
                    listaasignaturamalla_silabo = DetalleSilaboSemanalBibliografiaDocente.objects.values_list("silabosemanal__silabo__materia__asignaturamalla_id", flat=False).filter(librokohaprogramaanaliticoasignatura=libro).distinct("silabosemanal__silabo__materia__asignaturamalla")
                    data['selectmallas'] = Malla.objects.filter(Q(asignaturamalla__id__in=listaasignaturamalla_programa)|Q(asignaturamalla__id__in=listaasignaturamalla_silabo)).distinct() #& Q(asignaturamalla__materia__nivel__periodo=periodo)).distinct()
                    asignaturamalla = []
                    if 'mid' in request.GET:
                        if 'aid' in request.GET:
                            data['asigid'] = int(request.GET['aid'])
                            data['mid'] = int(request.GET['mid'])
                            if int(request.GET['aid']) > 0:
                                data['asignaturas'] = asignaturamalla = AsignaturaMalla.objects.filter(Q(id__in=listaasignaturamalla_programa) | Q(id__in=listaasignaturamalla_silabo)).distinct().filter(malla_id=int(request.GET['mid']))
                                asignaturamalla = AsignaturaMalla.objects.filter(Q(id__in=listaasignaturamalla_programa) | Q(id__in=listaasignaturamalla_silabo)).distinct().filter(pk=int(request.GET['aid']))
                            else:
                                data['mid'] = int(request.GET['mid'])
                                data['asigid'] = int(request.GET['aid'])
                                asignaturamalla = AsignaturaMalla.objects.filter(Q(id__in=listaasignaturamalla_programa) | Q(id__in=listaasignaturamalla_silabo)).distinct()
                        elif int(request.GET['mid']) > 0:
                            data['mid']=int(request.GET['mid'])
                            data['asignaturas'] = asignaturamalla = AsignaturaMalla.objects.filter(Q(id__in=listaasignaturamalla_programa) | Q(id__in=listaasignaturamalla_silabo)).distinct().filter(malla_id=int(request.GET['mid']))
                        else:
                            data['mid'] = int(request.GET['mid'])
                            asignaturamalla = AsignaturaMalla.objects.filter(Q(id__in=listaasignaturamalla_programa) | Q(id__in=listaasignaturamalla_silabo)).distinct()
                    else:
                        asignaturamalla = AsignaturaMalla.objects.filter(Q(id__in=listaasignaturamalla_programa) | Q(id__in=listaasignaturamalla_silabo)).distinct()
                    paging = MiPaginador(asignaturamalla, 20)
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
                    data['asignaturamalla'] = page.object_list
                    return render(request, "librosbiblioteca/detallelibro.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            if action == 'solicitudeslibros':
                try:
                    data['title'] = u'Solicitudes de adquisición de libros'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            solicitudes = SolicitudCompraLibro.objects.filter(Q(nombre__icontains=search)|
                                                                              Q(persona__nombres__icontains=search)|
                                                                              Q(persona__apellido1__icontains=search)|
                                                                              Q(persona__apellido2__icontains=search)|
                                                                              Q(programa__asignaturamalla__asignatura__nombre__icontains=search)|
                                                                              Q(programa__asignaturamalla__malla__carrera__nombre__icontains=search)|
                                                                              Q(autor__icontains=search)|
                                                                              Q(editorial__icontains=search)).order_by('fecha')
                        else:
                            solicitudes = SolicitudCompraLibro.objects.filter((Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])) |
                                                                              (Q(programa__asignaturamalla__asignatura__nombre__icontains=ss[0]) & Q(programa__asignaturamalla__asignatura__nombre__icontains=ss[1]))|
                                                                              (Q(programa__asignaturamalla__malla__carrera__nombre__icontains=ss[0]) & Q(programa__asignaturamalla__malla__carrera__nombre__icontains=ss[1]))|
                                                                              (Q(nombre__contains=ss[0]) & Q(nombre__icontains=ss[1]))|
                                                                              (Q(autor__contains=ss[0]) | Q(autor__icontains=ss[0])) |
                                                                              (Q(editorial__contains=ss[0]) & Q(editorial__icontains=ss[1])),
                                                                              status=True).order_by('fecha')
                    elif 'id' in request.GET:
                        ids = int(request.GET['id'])
                        solicitudes = SolicitudCompraLibro.objects.filter(id=ids)
                    else:
                        solicitudes = SolicitudCompraLibro.objects.filter(status=True).order_by('-fecha')
                    paging = MiPaginador(solicitudes, 20)
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
                    data['solicitudes'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "librosbiblioteca/solicitudeslibros.html", data)
                except Exception as ex:
                    pass

            if action == 'totalvisitalibros':
                try:
                    data['title'] = u'Visitas de libros'
                    data['visitaslibros'] = total = VisitasBiblioteca.objects.values_list('tipoperfil').filter(status=True).annotate(prom=Count('persona_id')).order_by('tipoperfil')
                    return render(request, "librosbiblioteca/totalvisitaslibros.html", data)
                except Exception as ex:
                    pass

            if action == 'bibliografias':
                try:
                    data['title'] = u'Bibliografias'
                    data['periodoid'] = periodo.id
                    listamalla = ProgramaAnaliticoAsignatura.objects.values_list("asignaturamalla__malla",flat=False).filter(asignaturamalla__materia__nivel__periodo=periodo).distinct('asignaturamalla__malla')
                    data['selectmallas'] =  Malla.objects.filter(id__in=listamalla).order_by('carrera', 'modalidad', '-inicio')
                    mallas = []
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        mallas = Malla.objects.filter(pk=ids).order_by('carrera', 'modalidad', '-inicio')
                    elif 'mid' in request.GET:
                        if int(request.GET['mid']) > 0:
                            data['mid']=int(request.GET['mid'])
                            listasignatura = ProgramaAnaliticoAsignatura.objects.values_list("asignaturamalla_id",flat=False).filter(asignaturamalla__malla=int(request.GET['mid']))
                            data['asignaturas'] = AsignaturaMalla.objects.filter(pk__in=listasignatura).order_by('nivelmalla','asignatura')
                            mallas = Malla.objects.filter(Q(id__in=listamalla),  Q(pk=int(request.GET['mid'])))
                        else:
                            data['mid'] = int(request.GET['mid'])
                            mallas = Malla.objects.filter(id__in=listamalla).order_by('carrera', 'modalidad', '-inicio')
                    else:
                        mallas = Malla.objects.filter(id__in=listamalla).order_by('carrera', 'modalidad', '-inicio')

                    data['asigid'] = 0
                    if 'aid' in request.GET:
                        data['asigid']= int(request.GET['aid'])
                    paging = MiPaginador(mallas, 1)
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
                    data['mallas'] = page.object_list
                    return render(request, "librosbiblioteca/bibliografia.html", data)
                except Exception as ex:
                    pass


            if action == 'catalogoLibro_excel':
                try:
                    idcoord = int(request.GET['idcoord'])
                    idcarrera = int(request.GET['idcarrera'])

                    if not idcoord == 0:
                        data['coordinacion'] = Coordinacion.objects.get(pk=int(idcoord)).nombre
                    else:
                        data['coordinacion'] = 'TODOS LAS COORDINACIONES'
                    if not idcarrera == 0:
                        data['carrera'] = Carrera.objects.get(pk=int(idcarrera)).nombre
                    else:
                        data['carrera'] = 'TODOS LAS CARRERAS'

                    __author__ = 'Unemi'

                    style_sb = easyxf('font: name Times New Roman, color-index black, bold off')
                    title = easyxf( 'font: name Times New Roman, color-index green, bold on , height 350; alignment: horiz centre')
                    title1 = easyxf( 'font: name Times New Roman, color-index green, bold on , height 250; alignment: horiz centre')
                    style_sb1 = easyxf('font: name Times New Roman, color-index black, bold on')
                    style_col = easyxf('font: name Times New Roman, color-index black, bold on; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    styrowD = easyxf('font: name Times New Roman, color-index black, bold off; borders: left thin, right thin, top thin, bottom thin')
                    styrow = easyxf( 'font: name Times New Roman, color-index black, bold off; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')


                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Libros Catalogados')
                    ws.write_merge(0, 0, 0, 5, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 5, 'REPORTE LISTADOS DE LIBROS CATALOGADOS', title1)
                    ws.write_merge(4, 4, 0, 0, 'COORDINACIÓN:  ', style_sb1)
                    ws.write_merge(4, 4, 1, 1, data['coordinacion'], style_sb)
                    ws.write_merge(5, 5, 0, 0, 'CARRERA: ', style_sb1)
                    ws.write_merge(5, 5, 1, 1, data['carrera'], style_sb)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Libros_Catalogados' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CÓDIGO", 3300),
                        (u"NOMBRE LIBRO", 11000),
                        (u"AUTOR", 10000),
                        (u"EDITORIAL", 4500),
                        (u"UBICACIÓN", 5000),
                        (u"CANTIDAD", 2900),
                    ]
                    row_num = 7
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], style_col)
                        ws.col(col_num).width = columns[col_num][1]

                    listalibros = LibroKohaProgramaAnaliticoAsignatura.objects.filter(status=True).order_by('nombre')

                    if not idcoord == 0:
                        listalibros = listalibros.filter(carrera__coordinacion__pk=int(idcoord) , status=True)
                    if not idcarrera == 0:
                        listalibros = listalibros.filter(carrera__id=idcarrera , status=True)



                    row_num = 8
                    for libros in listalibros:
                        if libros.codigokoha == 0:
                            ws.write(row_num, 0, 'SIN CÓDIGO', styrow)
                        else:
                            ws.write(row_num, 0, libros.codigokoha, styrow)
                        ws.write(row_num, 1, str(libros.nombre).upper(), styrowD)
                        ws.write(row_num, 2, str(libros.autor).upper(), styrowD)
                        ws.write(row_num, 3, (libros.editorial).upper(), styrow)
                        ws.write(row_num, 4, (libros.hilera).upper(), styrow)
                        ws.write(row_num, 5, libros.cantidad, styrow)
                        row_num += 1

                    row_num += 1
                    # ws.write(row_num, 4, 'TOTAL', styrow)
                    # ws.write(row_num, 5, listalibros.count(), styrow)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'catalogoLibro_pdf':
                try:

                    idcoord = int(request.GET['idcoord'])
                    idcarrera = int(request.GET['idcarrera'])

                    if not idcoord == 0:
                        data['coordinacion'] = Coordinacion.objects.get(pk=int(idcoord)).nombre
                    else:
                        data['coordinacion'] = 'TODOS LAS COORDINACIONES'
                    if not idcarrera == 0:
                        data['carrera'] = Carrera.objects.get(pk=int(idcarrera)).nombre
                    else:
                        data['carrera'] = 'TODOS LAS CARRERAS'

                    listalibros = LibroKohaProgramaAnaliticoAsignatura.objects.filter(status=True).order_by('nombre')

                    if not idcoord == 0:
                        listalibros = listalibros.filter(carrera__coordinacion__pk=int(idcoord), status=True)
                    if not idcarrera == 0:
                        listalibros = listalibros.filter(carrera__id=idcarrera, status=True)

                    data['libroCatalogo'] = listalibros

                    # data['total'] = listalibros.count()
                    data['fechahoy'] = datetime.now().date()
                    return conviert_html_to_pdf(
                        'librosbiblioteca/catalogolibropdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass


            if action == 'librosfacultadcarrera_excel':
                try:
                    idcoord = int(request.GET['idcoord'])
                    idcarrera = int(request.GET['idcarrera'])

                    if not idcoord == 0:
                        data['coordinacion'] = Coordinacion.objects.get(pk=int(idcoord)).nombre
                    else:
                        data['coordinacion'] = 'TODOS LAS COORDINACIONES'
                    if not idcarrera == 0:
                        data['carrera'] = Carrera.objects.get(pk=int(idcarrera)).nombre
                    else:
                        data['carrera'] = 'TODOS LAS CARRERAS'

                    perido_seleccionado = Periodo.objects.get(pk=int(encrypt(request.GET['periodo'])))

                    __author__ = 'Unemi'

                    style_sb = easyxf('font: name Times New     Roman, color-index black, bold off')
                    title = easyxf(
                        'font: name Times New Roman, color-index green, bold on , height 350; alignment: horiz centre')
                    title1 = easyxf(
                        'font: name Times New Roman, color-index green, bold on , height 250; alignment: horiz centre')
                    style_sb1 = easyxf('font: name Times New Roman, color-index black, bold on')
                    style_col = easyxf(
                        'font: name Times New Roman, color-index black, bold on; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    styrowD = easyxf(
                        'font: name Times New Roman, color-index black, bold off; borders: left thin, right thin, top thin, bottom thin')
                    styrow = easyxf('font: name Times New Roman, color-index black, bold off; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style_date = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre',num_format_str='yy/mm/dd h:mm')

                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Libros en Silabos')
                    ws.write_merge(0, 0, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 4, 'LIBROS REGISTRADOS EN EL SILABO', title1)
                    ws.write_merge(4, 4, 0, 0, 'COORDINACIÓN:  ', style_sb1)
                    ws.write_merge(4, 4, 1, 1, data['coordinacion'], style_sb)
                    ws.write_merge(5, 5, 0, 0, 'CARRERA: ', style_sb1)
                    ws.write_merge(5, 5, 1, 1, data['carrera'], style_sb)
                    ws.write_merge(6, 6, 0, 0, 'PERIODO: ', style_sb1)
                    ws.write_merge(6, 6, 1, 1, perido_seleccionado.nombre, style_sb)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Libros_Silabos_Fac' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"LIBRO", 11000),
                        # (u"CARRERA", 10000),
                        (u"DOCENTE", 10000),
                        (u"FECHA DE REGISTRO", 5000),
                        (u"CANTIDAD EXISTENTE", 5000),
                    ]
                    row_num = 8
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], style_col)
                        ws.col(col_num).width = columns[col_num][1]


                    silabos = Silabo.objects.filter(status=True, materia__nivel__periodo_id=perido_seleccionado.id,
                                                    materia__asignaturamalla__malla__carrera_id=idcarrera)

                    row_num = 9
                    for silabo in silabos:
                        tienelibro = silabo.tiene_libros_pertenecientes()
                        if tienelibro:
                            for libro in tienelibro:
                                ws.write(row_num, 0, str(libro.nombre).upper(), styrowD)
                                # ws.write(row_num, 1, str(silabo.materia.asignatura), styrow)
                                ws.write(row_num, 1, str(silabo.profesor), styrowD)
                                ws.write(row_num, 2, silabo.fecha_creacion, style_date)
                                ws.write(row_num, 3, libro.cantidad, styrow)
                                row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'librosilabo_li_excel':
                try:
                    perido_seleccionado = Periodo.objects.get(pk=int(encrypt(request.GET['periodo'])))
                    __author__ = 'Unemi'

                    title = easyxf(
                        'font: name Times New Roman, color-index green, bold on , height 350; alignment: horiz centre')
                    title1 = easyxf(
                        'font: name Times New Roman, color-index green, bold on , height 250; alignment: horiz centre')
                    style_col = easyxf(
                        'font: name Times New Roman, color-index black, bold on; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style_sb = easyxf('font: name Times New Roman, color-index black, bold on')
                    style_sb1 = easyxf('font: name Times New Roman, color-index black, bold on')
                    styrowN = easyxf('font: name Times New Roman, color-index black, bold off; alignment: horiz left; borders: left thin, right thin, top thin, bottom thin')
                    styrow = easyxf('font: name Times New Roman, color-index black, bold off; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style_date = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre', num_format_str='yy/mm/dd h:mm')

                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Libros en Silabos')
                    ws.write_merge(0, 0, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 4, 'LIBROS REGISTRADOS EN EL SILABO', title1)
                    ws.write_merge(4, 4, 0, 0, 'PERIODO: ', style_sb1)
                    ws.write_merge(4, 4, 1, 1, perido_seleccionado.nombre, style_sb)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Libros_Silabo' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"LIBRO", 11000),
                        (u"MATERIA", 10000),
                        (u"DOCENTE", 11000),
                        (u"FECHA DE REGISTRO", 5000),
                        (u"CANTIDAD EXISTENTE", 5000),
                    ]
                    row_num = 6
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], style_col)
                        ws.col(col_num).width = columns[col_num][1]

                    silabos = Silabo.objects.filter(status=True, materia__nivel__periodo_id=perido_seleccionado.id)
                    libro = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk=int(request.GET['libro']))

                    row_num = 7
                    for silabo in silabos:
                        tienelibro = silabo.tiene_libro(libro)
                        if tienelibro:
                            ws.write(row_num, 0, str(libro.nombre).upper(), styrowN)
                            ws.write(row_num, 1, str(silabo.materia.asignatura), styrow)
                            ws.write(row_num, 2, str(silabo.profesor), styrow)
                            ws.write(row_num, 3, silabo.fecha_creacion, style_date)
                            ws.write(row_num, 4, libro.cantidad, styrow)
                            row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'librosilabo_li_pdf':
                try:
                    perido_seleccionado = Periodo.objects.get(pk = int(encrypt(request.GET['periodo'])))
                    silabos = Silabo.objects.filter(status=True,materia__nivel__periodo_id=perido_seleccionado.id)
                    libro = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk = int(request.GET['libro']))

                    data['silabos'] = silabos
                    data['libro'] = libro
                    data['periodo_seleccionado'] = perido_seleccionado
                    data['fechahoy'] = datetime.now().date()

                    return conviert_html_to_pdf(
                        'librosbiblioteca/reporteporlibropdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'librosfacultadcarrera_pdf':
                try:
                    perido_seleccionado = Periodo.objects.get(pk = int(encrypt(request.GET['periodo'])))
                    carrera_seleccionada = Carrera.objects.get(pk = int(request.GET['carrera']))
                    facultad_seleccionada = carrera_seleccionada.coordinaciones()[0]
                    silabos = Silabo.objects.filter(status=True,materia__nivel__periodo_id=perido_seleccionado.id,
                                                    materia__asignaturamalla__malla__carrera_id = carrera_seleccionada.id)
                    # silabos = Silabo.objects.filter(status=True,materia__nivel__periodo_id=perido_seleccionado.id,
                    #                                 profesor__coordinacion__carrera_id = 1)


                    # libro = LibroKohaProgramaAnaliticoAsignatura.objects.get(pk = int(request.GET['libro']))
                    # contador = 1
                    # for silabo in silabos:
                    #     for libro in silabo.tiene_libros_pertenecientes():
                    #         print(libro)
                    #         print(contador)
                    #         contador += 1
                    #     print(str(silabo)+str(' ------- Nº'))

                    data['silabos'] = silabos
                    # data['libro'] = libro
                    data['periodo_seleccionado'] = perido_seleccionado
                    data['carrera_seleccionada'] = carrera_seleccionada
                    data['facultad_seleccionada'] = facultad_seleccionada
                    data['fechahoy'] = datetime.now().date()

                    return conviert_html_to_pdf(
                        'librosbiblioteca/reporteporlibrocarrerafacultadpdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de Libros'
            search = None
            ids = None
            tipobus = None
            inscripcionid = None
            # if 'id' in request.GET:
            #     data['tipobus'] = 2
            #     ids = request.GET['id'
            try:
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    librosinvestigacion = LibroKohaProgramaAnaliticoAsignatura.objects.filter((Q(nombre__icontains=search) |
                                                                                             Q(titulo__icontains=search) |
                                                                                             Q(autor__icontains=search) ),
                                                                                              status=True).order_by('nombre')
                else:
                    librosinvestigacion = LibroKohaProgramaAnaliticoAsignatura.objects.filter(status=True).order_by('nombre')
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
                except Exception as ex:
                    pass
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['coordinacion'] = Coordinacion.objects.filter(status=True)
                data['librosbiblioteca'] = page.object_list
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['libros'] = LibroKohaProgramaAnaliticoAsignatura.objects.filter(status=True)
                return render(request, "librosbiblioteca/view.html", data)
            except Exception as ex:
                pass



