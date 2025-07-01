# -*- coding: latin-1 -*-
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import Borders, easyxf, Workbook
from openpyxl import Workbook
from xlwt import *
import random
from django.db.models import Count
from decorators import secure_module, last_access
from mobile.views import make_thumb_fotopersona, make_thumb_picture
from settings import GENERAR_TUMBAIL, UTILIZA_GRUPOS_ALUMNOS
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import CargarFotoForm, AnilladoForm
from sga.funciones import MiPaginador, generar_nombre, log, convertir_fecha, convertir_fecha_hora
from datetime import datetime

from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Persona, FotoPersona, PerfilUsuario, EntregaCarnetPerfil, Coordinacion, Anillado, \
    TIPO_DE_SERVICIO, Profesor
from certi.models import ConfiguracionCarnet


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    usuario = request.user
    persona = request.session['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'cargarfoto':
                try:
                    persona = Persona.objects.get(pk=request.POST['id'])
                    form = CargarFotoForm(persona, request.FILES)
                    if form.is_valid():
                        newfile = request.FILES['foto']
                        newfile._name = generar_nombre("foto_", newfile._name)
                        foto = persona.foto()
                        if foto:
                            foto.foto = newfile
                        else:
                            foto = FotoPersona(persona=persona,
                                               foto=newfile)
                        foto.save(request)
                        log(u'Adicionó foto de persona: %s' % foto, request,"add")
                        make_thumb_picture(persona)
                        if GENERAR_TUMBAIL:
                            make_thumb_fotopersona(persona)
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"La imagen seleccionada no cumple los requisitos, de tamaño o formato o hubo un error al guardar fichero."})

            elif action == 'perfiles':
                try:
                    data = {}
                    persona = Persona.objects.get(pk=int(request.POST['id']))
                    data['perfiles'] = perfiles = persona.perfilusuario_set.all()
                    # SOLO TIPO DE CARNE FISIO IMPRESO
                    configuraciones = ConfiguracionCarnet.objects.filter(status=True, tipo=2)
                    if not configuraciones.values("id").exists():
                        raise NameError(u"No existe configuración de carné")

                    if not configuraciones.filter(tipo_perfil=1).exists():
                        data['reporte_0_msg'] = u"No existe configuración de carné para estudiantes"
                        data['reporte_0'] = None
                    else:
                        data['reporte_0_msg'] = None
                        data['reporte_0'] = configuraciones.filter(tipo_perfil=1)[0].reporte

                    if not configuraciones.filter(tipo_perfil=2).exists():
                        data['reporte_1_msg'] = u"No existe configuración de carné para administrativos"
                        data['reporte_1'] = None
                    else:
                        data['reporte_1_msg'] = None
                        data['reporte_1'] = configuraciones.filter(tipo_perfil=2)[0].reporte

                    if not configuraciones.filter(tipo_perfil=3).exists():
                        data['reporte_2_msg'] = u"No existe configuración de carné para docentes"
                        data['reporte_2'] = None
                    else:
                        data['reporte_2_msg'] = None
                        data['reporte_2'] = configuraciones.filter(tipo_perfil=3)[0].reporte

                    # data['reporte_0'] = obtener_reporte('carnet')
                    # data['reporte_1'] = obtener_reporte('carnet_admin')
                    # data['reporte_2'] = obtener_reporte('carnet_docente')
                    template = get_template("doc_credencial/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'nombre': persona.nombre_completo_inverso()})
                except Exception as ex:
                    # transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'entregado':
                try:
                    data = {}
                    observ = request.POST['observ'].upper()
                    perfil = PerfilUsuario.objects.get(pk=int(request.POST['id']))
                    if not perfil.entrego_carnet():
                        entrega = EntregaCarnetPerfil(perfilusuario=perfil,fecha=datetime.now().date())
                        entrega.observacion = observ
                        entrega.save(request)
                        log(u'Entrego carnet perfil: %s' % entrega, request, "add")
                    else:
                        entrega = perfil.entrega_carnet()
                        entrega.fecha = datetime.now().date()
                        entrega.observacion = observ
                        entrega.save(request)
                        log(u'Entrego carnet perfil: %s' % entrega, request, "edit")
                    return JsonResponse({"result": "ok", 'fecha': entrega.fecha.strftime('%d-%m-%Y'),'observacion': entrega.observacion})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addAnillado':
                try:
                    anillad = None
                    co = 0
                    f = AnilladoForm(request.POST)
                    if f.is_valid():
                        co = Coordinacion.objects.filter(inscripcion__perfilusuario__persona_id=int(f.cleaned_data['persona'])).distinct().last()
                        # coord = PerfilUsuario.objects.filter(persona=int(f.cleaned_data['persona'])).distinct('persona')
                        # print(coord.pk)
                        if co != None:
                            co=int(co.pk)
                        else:
                            try:
                                co = Profesor.objects.get(persona__id=int(f.cleaned_data['persona'])).coordinacion.pk
                            except Exception as e:
                                pass
                                co = 0

                        if co != 0:
                            anillad = Anillado(persona=Persona.objects.get(pk=int(f.cleaned_data['persona'])),
                                              coordinacion_id=co,
                                              cantidad=f.cleaned_data['cantidad'],
                                              tipo=f.cleaned_data['tipo'],
                                              observacion=f.cleaned_data['observacion'])
                        else:
                            anillad = Anillado(persona=Persona.objects.get(pk=int(f.cleaned_data['persona'])),
                                               cantidad=f.cleaned_data['cantidad'],
                                               tipo=f.cleaned_data['tipo'],
                                               observacion=f.cleaned_data['observacion'])

                        anillad.save(request)
                        log(u'Adiciono un nuevo Anillado: %s' % anillad, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as xe:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editAnillado':
                try:
                    f = AnilladoForm(request.POST)
                    if f.is_valid():
                        anilla = Anillado.objects.get(pk=request.POST['id'])
                        anilla.persona_id = f.cleaned_data['persona']
                        # anilla.coordinacion = f.cleaned_data['coordinacion']
                        anilla.cantidad = f.cleaned_data['cantidad']
                        anilla.tipo = f.cleaned_data['tipo']
                        anilla.observacion = f.cleaned_data['observacion']
                        anilla.save(request)
                        log(u'Edito un Anillado: %s' % anilla, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delAnillado':
                try:
                    ubicacion = Anillado.objects.get(pk=request.POST['id'])
                    ubicacion.status = False
                    ubicacion.save(request)
                    log(u'Elimino un Anillado: %s' % ubicacion, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'cargarfoto':
                try:
                    data['title'] = u'Subir foto'
                    data['persona'] = Persona.objects.get(pk=request.GET['id'])
                    form = CargarFotoForm()
                    data['form'] = form
                    return render(request, "doc_credencial/cargarfoto.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarsolicitante':
                try:
                    search = request.GET['q'].upper().strip()
                    ss = search.split(' ')
                    while '' in ss:
                        ss.remove('')

                    if len(ss) == 1:
                        personal = Persona.objects.filter(Q(nombres__icontains=search) |
                                                   Q(apellido1__icontains=search) |
                                                   Q(apellido2__icontains=search) |
                                                   Q(cedula__icontains=search) |
                                                   Q(pasaporte__icontains=search) |
                                                   Q(inscripcion__identificador__icontains=search) |
                                                   Q(
                                                       inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                   Q(inscripcion__carrera__nombre__icontains=search)).exclude(perfilusuario__empleador__isnull=False).distinct()
                    else:
                        personal = Persona.objects.filter(Q(apellido1__icontains=ss[0]) &
                                                   Q(apellido2__icontains=ss[1])).exclude(perfilusuario__empleador__isnull=False).distinct()
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_alias()} for x in personal]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addAnillado':
                try:
                    data['title'] = u'Nuevo Anillado'
                    # form.fields['persona'].queryset  = Persona.objects.exclude(perfilusuario__empleador__isnull=False).distinct()
                    # data['form'] = form
                    data['form'] = AnilladoForm()
                    return render(request, "doc_credencial/addAnillado.html", data)
                except Exception as ex:
                    pass

            elif action == 'editAnillado':
                try:
                    data['title'] = u'Editar Anillado'
                    data['pers'] = anillad = Anillado.objects.get(pk=int(request.GET['id']))

                    form = AnilladoForm(initial={
                                              'cantidad': anillad.cantidad,
                                              'tipo': anillad.tipo,
                                              'observacion': anillad.observacion})
                    if anillad.persona:
                        form.editar(anillad.persona)

                    data['form'] = form
                    return render(request, "doc_credencial/editAnillado.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewAnillado':
                data['title'] = u'Credenciales'
                search = None
                ids = None
                idC = 0
                idservicio = 0
                id_tipo_coord =0
                id_tipo_serv = 0
                try:
                    # personalAni = Persona.objects.exclude(perfilusuario__empleador__isnull=False).distinct()
                    personalAni = Anillado.objects.filter( status=True)

                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        while '' in ss:
                            ss.remove('')
                        if 'tipo_coord' in request.GET and len(ss) == 1:
                            id_tipo_coord = int(request.GET['tipo_coord'])
                            if id_tipo_coord !=0:
                                personalAni = personalAni.filter(Q(persona__nombres__icontains=search) |
                                                           Q(perfilusuario__inscripcion__coordinacion=id_tipo_coord) |
                                                           Q(persona__apellido1__icontains=search) |
                                                           Q(persona__apellido2__icontains=search) |
                                                           Q(persona__cedula__icontains=search) |
                                                           Q(persona__pasaporte__icontains=search) |
                                                           Q(persona__inscripcion__identificador__icontains=search) |
                                                           Q(persona__inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                           Q(persona__inscripcion__carrera__nombre__icontains=search)).distinct()
                        if 'tipo_serv' in request.GET and len(ss) == 1:
                            id_tipo_serv = int(request.GET['tipo_serv'])
                            if id_tipo_serv != 0:
                                personalAni = personalAni.filter(Q(persona__nombres__icontains=search) |
                                                           Q(tipo=id_tipo_serv) |
                                                           Q(persona__apellido1__icontains=search) |
                                                           Q(persona__apellido2__icontains=search) |
                                                           Q(persona__cedula__icontains=search) |
                                                           Q(persona__pasaporte__icontains=search) |
                                                           Q(persona__inscripcion__identificador__icontains=search) |
                                                           Q(persona__inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                           Q(persona__inscripcion__carrera__nombre__icontains=search)).distinct()
                        else:
                            if len(ss) == 1:
                                personalAni = personalAni.filter(Q(persona__nombres__icontains=search) |
                                                           Q(persona__apellido1__icontains=search) |
                                                           Q(persona__apellido2__icontains=search) |
                                                           Q(persona__cedula__icontains=search) |
                                                           Q(persona__pasaporte__icontains=search) |
                                                           Q(persona__inscripcion__identificador__icontains=search) |
                                                           Q(persona__inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                           Q(persona__inscripcion__carrera__nombre__icontains=search)).distinct()
                            else:
                                personalAni = personalAni.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                           Q(persona__apellido2__icontains=ss[1])).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        personalAni = personalAni.filter(id=ids)

                    if 'tipo_coord' in request.GET:
                        idC = int(request.GET['tipo_coord'])
                        if idC != 0:
                            if idC == 403:
                                personalAni = personalAni.filter(coordinacion__isnull=True)
                            else:
                                personalAni = personalAni.filter(coordinacion=idC)
                    if 'tipo_serv' in request.GET:
                        id_tipo_serv = int(request.GET['tipo_serv'])
                        if id_tipo_serv != 0:
                            personalAni = personalAni.filter(tipo=id_tipo_serv, status=True)

                    pagingAni = MiPaginador(personalAni, 25)
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
                            page = pagingAni.page(p)
                        except:
                            p = 1
                        page = pagingAni.page(p)
                    except Exception as ex:
                        page = pagingAni.page(p)
                    request.session['paginador'] = p
                    data['administrador'] = persona
                    data['persona_id'] = persona.id
                    data['servicio'] = TIPO_DE_SERVICIO
                    data['idservicio'] = id_tipo_serv
                    data['coordanillado'] = Coordinacion.objects.filter(status=True)
                    data['idcoordA'] = idC
                    data['cargo'] = '(' + persona.distributivopersona_set.get(regimenlaboral_id=1, status=True,
                                                                              estadopuesto=1).denominacionpuesto.descripcion + ')' if persona.distributivopersona_set.filter( regimenlaboral_id=1, status=True, estadopuesto=1) else ''
                    data['pagingAni'] = pagingAni
                    data['rangospaging'] = pagingAni.rangos_paginado(p)
                    data['page'] = page
                    data['searchanillado'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['personalAni'] = page.object_list
                    data['utiliza_grupos_alumnos'] = UTILIZA_GRUPOS_ALUMNOS
                    data['active']=2
                    return render(request, "doc_credencial/view.html", data)
                except Exception as ex:
                    pass

            elif action == 'delAnillado':
                try:
                    data['title'] = u'Confirmar eliminar el Anillado'
                    data['anillado'] = Anillado.objects.get(pk=int(request.GET['id']))
                    return render(request, "doc_credencial/delanillado.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteanillado_excel':
                try:
                    facultad = None

                    fechahasta =  convertir_fecha_hora(request.GET['hasta'] + " 23:59")
                    idcoord = int(request.GET['idcoord'])

                    if not idcoord == 0:
                        if idcoord == 403:
                            data['coordinacion'] = 'ADMINISTRATIVOS'
                        else:
                            facultad = Coordinacion.objects.get(pk=int(idcoord), status=True)
                            data['coordinacion'] = Coordinacion.objects.get(pk=int(idcoord)).nombre
                    else:
                        data['coordinacion'] = 'TODOS LAS FACULTADES'

                    __author__ = 'Unemi'
                    styrowD = easyxf(
                        'font: name Times New Roman, color-index black, bold off; borders: left thin, right thin, top thin, bottom thin')
                    styrow = easyxf(
                        'font: name Times New Roman, color-index black, bold off; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style_col = easyxf(
                        'font: name Times New Roman, color-index black, bold on; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style_sb1 = easyxf('font: name Times New Roman, color-index black, bold on')
                    style_sb = easyxf('font: name Times New Roman, color-index black, bold off')
                    title = easyxf(
                        'font: name Times New Roman, color-index green, bold on , height 350; alignment: horiz centre')
                    title1 = easyxf(
                        'font: name Times New Roman, color-index green, bold on , height 250; alignment: horiz centre')
                    style1 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre', num_format_str='yy/mm/dd h:mm')

                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Anillados')

                    ws.write_merge(0, 0, 0, 5, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 5, 'ÁREA DE IMPRENTA', title1)
                    ws.write_merge(2, 2, 0, 5, 'REPORTE DE ANILLADOS', title1)
                    ws.write_merge(4, 4, 0, 0, 'PERIODO:  ', style_sb1)
                    ws.write_merge(4, 4, 1, 1, 'DESDE  ' + request.GET['de'] + ' HASTA  ' + request.GET['hasta'],
                                   style_sb)
                    ws.write_merge(5, 5, 0, 0, 'FACULTAD: ', style_sb1)
                    ws.write_merge(5, 5, 1, 1, data['coordinacion'], style_sb)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=ReporteAnillado ' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"APELLIDOS Y NOMBRES", 10000),
                        (u"COORDINACIÓN", 10000),
                        (u"N° CÉDULA", 4500),
                        (u"CANTIDAD", 4500),
                        (u"TIPO", 4500),
                        (u"FECHA DE EJECUCIÓN", 5100),
                    ]
                    row_num = 8
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], style_col)
                        ws.col(col_num).width = columns[col_num][1]

                    personalAni = Anillado.objects.filter(status=True)
                    # personal = Persona.objects.exclude(perfilusuario__empleador__isnull=False).distinct()
                    if not idcoord == 0:
                        if idcoord == 403:
                            personalAni = personalAni.filter(coordinacion__isnull=True,
                                                             fecha_creacion__range=(
                                                                 convertir_fecha(request.GET['de']),
                                                                 fechahasta),
                                                             status=True)
                        else:
                            personalAni = personalAni.filter(coordinacion=idcoord,
                                                              fecha_creacion__range=(
                                                                  convertir_fecha(request.GET['de']),
                                                                  fechahasta),
                                                              status=True)
                    else:
                        personalAni = personalAni.filter(fecha_creacion__range=(
                                    convertir_fecha(request.GET['de']),
                                    fechahasta), status=True)

                    row_num = 9
                    # date_format = xlwt.XFStyle()
                    # date_format.num_format_str = 'yyyy/mm/dd h:mm:ss'

                    for pers in personalAni:
                        entrega = 0
                        ws.write(row_num, 0, str(pers.persona.nombre_completo_inverso()), styrowD)
                        if pers.coordinacion == None:
                            ws.write(row_num, 1, 'ADMINISTRATIVO', styrow)
                        else:
                            ws.write(row_num, 1, pers.coordinacion.nombre, styrow)
                        ws.write(row_num, 2, pers.persona.cedula, styrow)
                        ws.write(row_num, 3, pers.cantidad, styrow)
                        if pers.tipo == 1:
                            ws.write(row_num, 4, 'COPIA', styrow)
                        else:
                            ws.write(row_num, 4, 'IMPRESIÓN', styrow)
                        ws.write(row_num, 5, pers.fecha_creacion, style1)

                        row_num += 1
                    row_num += 1
                    ws.write(row_num, 4, 'TOTAL', styrow)
                    ws.write(row_num, 5, personalAni.count(), styrow)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteanillado_pdf':
                try:

                    facultad = None
                    fechahasta =  convertir_fecha_hora(request.GET['hasta'] + " 23:59")
                    idcoord = int(request.GET['idcoord'])

                    if not idcoord == 0:
                        if idcoord == 403:
                            data['coordinacion'] = 'ADMINISTRATIVOS'
                        else:
                            facultad = Coordinacion.objects.get(pk=int(idcoord), status=True)
                            data['coordinacion'] = Coordinacion.objects.get(pk=int(idcoord)).nombre
                    else:
                        data['coordinacion'] = 'TODOS LAS FACULTADES'

                    personalAni = Anillado.objects.filter(status=True)
                    if not idcoord == 0:
                        if idcoord == 403:
                            personalAni = personalAni.filter(coordinacion__isnull=True,
                                                             fecha_creacion__range=(
                                                                 convertir_fecha(request.GET['de']),
                                                                 fechahasta),
                                                             status=True)
                        else:
                            personalAni = personalAni.filter(coordinacion=idcoord,
                                                         fecha_creacion__range=(
                                                             convertir_fecha(request.GET['de']),
                                                             fechahasta),
                                                         status=True)
                    else:
                        personalAni = personalAni.filter(fecha_creacion__range=(
                            convertir_fecha(request.GET['de']),
                            fechahasta), status=True)

                    data['anillado'] = personalAni

                    data['total'] = personalAni.count()
                    data['desde'] = request.GET['de']
                    data['hasta'] = request.GET['hasta']
                    data['fechahoy'] = datetime.now().date()
                    data['idcoord'] = idcoord
                    return conviert_html_to_pdf(
                        'doc_credencial/reporteanilladopdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'reportegeneral_excel':
                try:
                    facultad = None
                    fechadesde = request.GET['de']
                    fechahasta = request.GET['hasta']
                    idcoord = int(request.GET['idcoord'])

                    if not idcoord == 0:
                        facultad = Coordinacion.objects.get(pk=int(idcoord),status=True)
                        data['coordinacion'] = Coordinacion.objects.get(pk=int(idcoord)).nombre
                    else:
                        data['coordinacion'] = 'TODOS LAS FACULTADES'

                    __author__ = 'Unemi'
                    styrowD = easyxf('font: name Times New Roman, color-index black, bold off; borders: left thin, right thin, top thin, bottom thin')
                    styrow = easyxf('font: name Times New Roman, color-index black, bold off; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style_col = easyxf('font: name Times New Roman, color-index black, bold on; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style_sb1 = easyxf('font: name Times New Roman, color-index black, bold on')
                    style_sb = easyxf('font: name Times New Roman, color-index black, bold off')
                    title = easyxf( 'font: name Times New Roman, color-index green, bold on , height 350; alignment: horiz centre')
                    title1 = easyxf( 'font: name Times New Roman, color-index green, bold on , height 250; alignment: horiz centre')
                    style_date = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre', num_format_str='yy/mm/dd h:mm')

                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Reporte Credencial')

                    ws.write_merge(0, 0, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 4, 'ÁREA DE IMPRENTA', title1)
                    ws.write_merge(2, 2, 0, 4, 'REPORTE DE CREDENCIAL', title1)
                    ws.write_merge(4, 4, 0, 0, 'PERIODO:  ', style_sb1)
                    ws.write_merge(4, 4, 1, 1, 'DESDE  ' + request.GET['de'] + ' HASTA  ' + request.GET['hasta'], style_sb)
                    ws.write_merge(5, 5, 0, 0, 'FACULTAD: ', style_sb1)
                    ws.write_merge(5, 5, 1, 1, data['coordinacion'], style_sb)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=ReporteCredencial ' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"APELLIDOS Y NOMBRES", 10000),
                        (u"FACULTAD", 10000),
                        (u"N° CÉDULA", 4500),
                        (u"N° REGISTRO", 4500),
                        (u"HORA", 5100),

                    ]
                    row_num = 9
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], style_col)
                        ws.col(col_num).width = columns[col_num][1]

                    personal = Persona.objects.exclude(perfilusuario__empleador__isnull=False).distinct()
                    if not idcoord ==0:
                        personal = EntregaCarnetPerfil.objects.filter(perfilusuario__inscripcion__coordinacion=idcoord,
                                                                      fecha_creacion__range=(
                                                                          convertir_fecha(request.GET['de']),
                                                                          convertir_fecha(request.GET['hasta'])),
                                                                      status=True)
                    else:
                        personal= EntregaCarnetPerfil.objects.filter(fecha_creacion__range=(
                                                                     convertir_fecha(request.GET['de']),
                                                                     convertir_fecha(request.GET['hasta'])),
                                                                     status = True)

                    row_num = 10
                    # date_format = xlwt.XFStyle()
                    # date_format.num_format_str = 'yyyy/mm/dd h:mm:ss'

                    for pers in personal:
                        entrega = 0

                        ws.write(row_num, 0, str(pers.perfilusuario.persona.nombre_completo_inverso()) , styrowD)
                        ws.write(row_num, 1, str(pers.perfilusuario.inscripcion.coordinacion.nombre), styrow)
                        ws.write(row_num, 2, pers.perfilusuario.persona.cedula, styrow)
                        idp=pers.perfilusuario.persona.id
                        # entrega = EntregaCarnetPerfil.objects.filter(perfilusuario__persona__id=idp, fecha_creacion__isnull=False, status=True).count()
                        entrega = pers.contar_entregados(idp)
                        ws.write(row_num, 3, entrega, styrow)

                        ws.write(row_num, 4, pers.fecha_creacion, style_date)
                        # fechaE = (pers.fecha_creacion, date_format)
                        # ws.write(row_num, 4, str(fechaE), styrow)

                        row_num += 1

                    row_num += 1
                    ws.write(row_num, 3, 'TOTAL', styrow)
                    ws.write(row_num, 4, personal.count(), styrow)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportegeneral_pdf':
                try:

                    facultad = None
                    fechadesde = request.GET['de']
                    fechahasta = request.GET['hasta']
                    idcoord = int(request.GET['idcoord'])

                    if not idcoord == 0:
                        facultad = Coordinacion.objects.get(pk=int(idcoord), status=True)
                        data['coordinacion'] = Coordinacion.objects.get(pk=int(idcoord)).nombre
                    else:
                        data['coordinacion'] = 'TODOS LAS FACULTADES'

                    if not idcoord == 0:
                        personal = EntregaCarnetPerfil.objects.filter(perfilusuario__inscripcion__coordinacion=idcoord,
                                                                      fecha_creacion__range=(
                                                                          convertir_fecha(request.GET['de']),
                                                                          convertir_fecha(request.GET['hasta'])),
                                                                      status=True).distinct()
                    else:
                        personal = EntregaCarnetPerfil.objects.filter(fecha_creacion__range=(
                            convertir_fecha(request.GET['de']),
                            convertir_fecha(request.GET['hasta'])),
                            status=True).distinct()

                    data['credencial'] = personal

                    data['total'] = personal.count()
                    data['desde'] = fechadesde
                    data['hasta'] = fechahasta
                    data['fechahoy'] = datetime.now().date()
                    return conviert_html_to_pdf(
                        'doc_credencial/reportecredencialpdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Credenciales'
            search = None
            ids = None
            idC = 0
            try:
                personal = Persona.objects.exclude(perfilusuario__empleador__isnull=False).distinct()
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    while '' in ss:
                        ss.remove('')
                    if 'tipo_coord' in request.GET and len(ss) == 1:
                        personal = personal.filter(Q(nombres__icontains=search) |
                                                   Q(perfilusuario__inscripcion__coordinacion=idC) |
                                                   Q(apellido1__icontains=search) |
                                                   Q(apellido2__icontains=search) |
                                                   Q(cedula__icontains=search) |
                                                   Q(pasaporte__icontains=search) |
                                                   Q(inscripcion__identificador__icontains=search) |
                                                   Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                   Q(inscripcion__carrera__nombre__icontains=search)).distinct()
                    else:
                        if len(ss) == 1:
                            personal = personal.filter(Q(nombres__icontains=search) |
                                                       Q(apellido1__icontains=search) |
                                                       Q(apellido2__icontains=search) |
                                                       Q(cedula__icontains=search) |
                                                       Q(pasaporte__icontains=search) |
                                                       Q(inscripcion__identificador__icontains=search) |
                                                       Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                       Q(inscripcion__carrera__nombre__icontains=search)).distinct()
                        else:
                            personal = personal.filter(Q(apellido1__icontains=ss[0]) &
                                                   Q(apellido2__icontains=ss[1])).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    personal = personal.filter(id=ids)

                if 'tipo_coord' in request.GET:
                    idC = int(request.GET['tipo_coord'])
                    if idC != 0:
                        personal = personal.filter(perfilusuario__inscripcion__coordinacion=idC)

                paging = MiPaginador(personal, 25)
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
                    page = paging.page(p)
                request.session['paginador'] = p
                data['administrador'] = persona
                data['persona_id'] = persona.id
                data['coordinacion'] = Coordinacion.objects.filter(status=True)
                data['idcoord'] = idC
                data['cargo'] = '(' + persona.distributivopersona_set.get(regimenlaboral_id=1, status=True, estadopuesto=1).denominacionpuesto.descripcion + ')' if persona.distributivopersona_set.filter(regimenlaboral_id=1, status=True, estadopuesto=1) else ''
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['personal'] = page.object_list
                data['utiliza_grupos_alumnos'] = UTILIZA_GRUPOS_ALUMNOS
                data['active'] = 1
                return render(request, "doc_credencial/view.html", data)
            except Exception as ex:
                    pass
