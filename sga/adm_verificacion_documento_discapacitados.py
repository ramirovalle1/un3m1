# -*- coding: UTF-8 -*-
import random

from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q ,Case , Value, CharField, When
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import json
from django.template import Context
from django.template.loader import get_template
from datetime import datetime

from xlwt import easyxf, XFStyle, Workbook

from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from sagest.forms import DeportistaValidacionForm, DiscapacidadValidacionForm
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import SolicitudForm, TipoDiscapacidadForm, SubTipoDiscapacidadForm
from django.db.models.aggregates import Avg
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import RecordAcademico, SolicitudMatricula, SolicitudDetalle, Matricula, MateriaAsignada, TipoSolicitud, \
    ConfiguracionTerceraMatricula, Inscripcion, DeportistaPersona, Carrera, DisciplinaDeportiva, PerfilInscripcion, \
    Coordinacion, NivelMalla, Discapacidad, SubTipoDiscapacidad, Profesor, ProfesorMateria ,Aula
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'validar':
            try:
                form = DiscapacidadValidacionForm(request.POST)
                if form.is_valid():
                    discapacidad = PerfilInscripcion.objects.get(pk=int(request.POST['id']))
                    discapacidad.estadoarchivodiscapacidad = form.cleaned_data['estadodiscapacidad']
                    discapacidad.observacionarchdiscapacidad = form.cleaned_data['observaciondiscapacidad'].strip().upper()
                    discapacidad.verificadiscapacidad = True if int(form.cleaned_data['estadodiscapacidad']) == 2 else False
                    discapacidad.tipodiscapacidad = form.cleaned_data['tipodiscapacidad']
                    discapacidad.porcientodiscapacidad = form.cleaned_data['porcientodiscapacidad']

                    if not form.cleaned_data['tipodiscapacidad'] and form.cleaned_data['tipodiscapacidadmultiple']:
                        raise NameError('No puede elegir discapacidades multiples sin elegir una discapacidad principal')
                    if form.cleaned_data['tienediscapacidadmultiple'] and not form.cleaned_data['tipodiscapacidadmultiple']:
                        raise NameError('Debe elegir una o más discapacidades multiples')
                    discapacidad.carnetdiscapacidad = form.cleaned_data['carnetdiscapacidad']
                    discapacidad.institucionvalida = form.cleaned_data['institucionvalida']
                    discapacidad.tienediscapacidadmultiple = form.cleaned_data['tienediscapacidadmultiple']
                    discapacidad.grado = form.cleaned_data['grado'] if form.cleaned_data['grado'] else 0
                    discapacidad.save(request)
                    discapacidad.tipodiscapacidadmultiple.clear()
                    discapacidad.subtipodiscapacidad.clear()
                    if form.cleaned_data['tienediscapacidadmultiple']:
                        tipos = request.POST.getlist('tipodiscapacidadmultiple')
                        for tipo in tipos:
                            discapacidad.tipodiscapacidadmultiple.add(tipo)
                    if form.cleaned_data['tipodiscapacidad']:
                        subtipos = request.POST.getlist('subtipodiscapacidad')
                        for subtipo in subtipos:
                            discapacidad.subtipodiscapacidad.add(subtipo)
                    log(u'Actualizó registro de discapacidad: %s' % discapacidad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddiscapacidad':
            try:
                f = TipoDiscapacidadForm(request.POST)
                if f.is_valid():
                    if Discapacidad.objects.filter(status=True, nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": True, 'mensaje':'Ya existe discapacidad con ese nombre'}, safe=False)
                    tipodiscapacidad = Discapacidad(nombre=f.cleaned_data['nombre'],
                                                    codigo_tthh=f.cleaned_data['codigo_tthh'])
                    tipodiscapacidad.save(request)
                    log(u'Agrego tipo de discapacidad: %s' % tipodiscapacidad, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
        elif action == 'editdiscapacidad':
            try:
                data['id'] = id = request.POST['id']
                tipodiscapacidad = Discapacidad.objects.get(id=id)
                f = TipoDiscapacidadForm(request.POST)
                if f.is_valid():
                    if Discapacidad.objects.filter(status=True, nombre=f.cleaned_data['nombre']).exclude(id=id).exists():
                        return JsonResponse({"result": True, 'mensaje':'Ya existe discapacidad con ese nombre'}, safe=False)
                    tipodiscapacidad.nombre = f.cleaned_data['nombre']
                    tipodiscapacidad.codigo_tthh = f.cleaned_data['codigo_tthh']
                    tipodiscapacidad.save(request)
                    log(u'Edito tipo de discapacidad: %s' % tipodiscapacidad, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
        elif action == 'deldiscapacidad':
            try:
                data['id'] = id = request.POST['id']
                tipodiscapacidad = Discapacidad.objects.get(id=id)
                tipodiscapacidad.status = False
                tipodiscapacidad.save(request)
                log(u'Elimino tipo de discapacidad: %s' % tipodiscapacidad, request, "del")
                return JsonResponse({"result": 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'addsubtipodiscapacidad':
            try:
                f = SubTipoDiscapacidadForm(request.POST)
                if f.is_valid():
                    if SubTipoDiscapacidad.objects.filter(discapacidad_id=request.POST['tipo'],status=True, nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": True, 'mensaje':'Ya existe discapacidad con ese nombre'}, safe=False)
                    tipodiscapacidad = SubTipoDiscapacidad(discapacidad_id=request.POST['tipo'],
                                            nombre=f.cleaned_data['nombre'], descripcion=f.cleaned_data['descripcion'])
                    tipodiscapacidad.save(request)
                    log(u'Agrego subtipo de discapacidad: %s' % tipodiscapacidad, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
        elif action == 'editsubtipodiscapacidad':
            try:
                data['id'] = id = request.POST['id']
                tipodiscapacidad = SubTipoDiscapacidad.objects.get(id=id)
                f = SubTipoDiscapacidadForm(request.POST)
                if f.is_valid():
                    if SubTipoDiscapacidad.objects.filter(status=True, nombre=f.cleaned_data['nombre']).exclude(id=id).exists():
                        return JsonResponse({"result": True, 'mensaje':'Ya existe un sub tipo de discapacidad con ese nombre'}, safe=False)
                    tipodiscapacidad.nombre = f.cleaned_data['nombre']
                    tipodiscapacidad.descripcion = f.cleaned_data['descripcion']
                    tipodiscapacidad.save(request)
                    log(u'Edito subtipo de discapacidad: %s' % tipodiscapacidad, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
        elif action == 'delsubtipodiscapacidad':
            try:
                data['id'] = id = request.POST['id']
                tipodiscapacidad = SubTipoDiscapacidad.objects.get(id=id)
                tipodiscapacidad.status = False
                tipodiscapacidad.save(request)
                log(u'Elimino subtipo de discapacidad: %s' % tipodiscapacidad, request, "del")
                return JsonResponse({"result": 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'datos':
                try:
                    discapacitado = PerfilInscripcion.objects.get(pk=int(request.GET['id']))
                    data['discapacitado'] = discapacitado
                    form = DiscapacidadValidacionForm(initial={
                        'estadodiscapacidad': discapacitado.estadoarchivodiscapacidad,
                        'observaciondiscapacidad': discapacitado.observacionarchdiscapacidad,
                        'tipodiscapacidad': discapacitado.tipodiscapacidad,
                        'porcientodiscapacidad': discapacitado.porcientodiscapacidad,
                        'carnetdiscapacidad': discapacitado.carnetdiscapacidad,
                        'institucionvalida': discapacitado.institucionvalida,
                        'tienediscapacidadmultiple': discapacitado.tienediscapacidadmultiple,
                        'tipodiscapacidadmultiple': discapacitado.tipodiscapacidadmultiple.all(),
                        'grado': discapacitado.grado,
                        'subtipodiscapacidad': discapacitado.subtipodiscapacidad.all(),
                        'archivo': discapacitado.archivo

                    })
                    form.editar()
                    form.fields['estadodiscapacidad'].choices = (
                                ('', u'--Seleccione--'),
                                (2, u'VALIDADO'),
                                (3, u'RECHAZADO'),
                                (5, u'REVISIÓN'),
                                (6, u'RECHAZADO IO')
                    )

                    data['form'] = form
                    template = get_template("adm_verificacion_documento/discapacitados/datos.html")
                    return JsonResponse({"result": True, 'datos': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': u'Error al obtener los datos'})

            if action == 'descargar':
                try:
                    __author__ = 'UNEMI'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=estudiantes_discapacidad_' + random.randint(1,
                                                                                                                   10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 3000),
                        (u"ESTUDIANTE", 12000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO INSTITUCIONAL", 8000),
                        (u"TELEFONOS", 6000),
                        (u"CARRERA", 12000),
                        (u"FACULTAD", 12000),
                        (u"SECCION", 6000),
                        (u"NIVEL", 6000),
                        (u"DISCAPACIDAD", 6000),
                        (u"PORCENTAJE", 6000),
                        (u"CARNET", 6000),
                        (u"BECA", 6000),
                        (u"VERIFICADO POR LA UBE", 6000),
                        (u"SEXO", 6000),
                        (u"BLOQUE", 6000),
                        (u"CURSO", 6000)
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    discapacitados = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo,
                                                             persona__perfilinscripcion__tienediscapacidad=True).order_by("persona")
                    if 's' in request.GET:
                        search = request.GET['s']
                        discapacitados = discapacitados.filter(Q(persona__nombres__icontains=search) |
                                                               Q(persona__cedula__icontains=search) |
                                                               Q(persona__apellido1__icontains=search) |
                                                               Q(persona__apellido2__icontains=search)
                                                               )
                    if 'veri' in request.GET:
                        verificacion = int(request.GET['veri'])
                        if verificacion > 0:
                            discapacitados = discapacitados.filter(persona__perfilinscripcion__verificadiscapacidad=int(request.GET['veri']) == 1)
                    if 'c' in request.GET:
                        carreraselect = int(request.GET['c'])
                        if carreraselect > 0:
                            discapacitados = discapacitados.filter(carrera_id=carreraselect)
                    if 'm' in request.GET:
                        modalidadselect = int(request.GET['m'])
                        if modalidadselect > 0:
                            discapacitados = discapacitados.filter(modalidad_id=modalidadselect)
                    row_num = 1
                    for r in discapacitados:
                        i = 0
                        campo1 = r.persona.cedula
                        campo2 = r.persona.__str__()
                        campo3 = r.persona.email
                        campo4 = r.persona.emailinst
                        campo5 = "%s - %s" % (r.persona.telefono, r.persona.telefono_conv)
                        campo15 = r.coordinacion.__str__()
                        campo6 = r.carrera.__str__()
                        campo7 = r.sesion.nombre
                        campo8 = r.matricula_set.filter(nivel__periodo=periodo)[0].nivelmalla.nombre
                        campo9 = ""
                        if r.persona.mi_perfil():
                            if r.persona.mi_perfil().tipodiscapacidad:
                                campo9 = r.persona.mi_perfil().tipodiscapacidad.nombre
                        campo10 = ("%s" % r.persona.mi_perfil().porcientodiscapacidad) + "%"
                        campo11 = r.persona.mi_perfil().carnetdiscapacidad
                        campo12 = "BECADO" if r.tiene_registro_becario() else "NO BECADO"
                        campo13 = "SI" if r.persona.mi_perfil().verificadiscapacidad else "NO"
                        campo14 = r.persona.sexo.nombre if r.persona.sexo else ''
                        au = Aula.objects.filter(clase__materia__materiaasignada__matricula__in=r.matricula_set.all(),
                                                 clase__materia__materiaasignada__materia__asignaturamalla__transversal=False
                                                 ).order_by('bloque').first()
                        campo16 = au.bloque.descripcion if au.bloque else ''
                        campo17 = au.nombre if au.nombre else ''
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo15, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, font_style2)
                        ws.write(row_num, 12, campo12, font_style2)
                        ws.write(row_num, 13, campo13, font_style2)
                        ws.write(row_num, 14, campo14, font_style2)
                        ws.write(row_num, 15, campo16, font_style2)
                        ws.write(row_num, 16, campo17, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            # TIPO DE DISCAPACIDAD
            if action == 'descargardocentes':
                try:
                    __author__ = 'UNEMI'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_styl = XFStyle()
                    font_styl.font.bold = True
                    font_styl2 = XFStyle()
                    font_styl2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=docente-estudiantes_discapacidad_' + random.randint(1,
                                                                                                                   10000).__str__() + '.xls'
                    columns = [
                        #(u"PROFESOR MATERIA ID", 12000),
                        (u"DOCENTE", 12000),
                        (u"CORREO INSTITUCIONAL", 8000),
                        (u"TELEFONO", 8000),
                        (u"CARRERA", 12000),
                        (u"MATERIA", 12000),
                        (u"PARALELO", 12000),
                        #(u"CEDULA", 3000),
                        (u"ESTUDIANTE", 12000),
                        (u"DISCAPACIDAD", 7000),
                        (u"PORCENTAJE DISCAPACIDAD", 5000)

                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_styl)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 1
                    for materia in ProfesorMateria.objects.filter(status=True, profesor__status=True, profesor__activo=True, materia__status=True, materia__nivel__status=True, materia__nivel__periodo_id=periodo).order_by('profesor_id'):
                        if materia.materia.materiaasignada_set.filter(status=True, matricula__estado_matricula__in=[2, 3]).exists():
                            idpersonas = materia.materia.materiaasignada_set.values_list("matricula__inscripcion__persona__id", flat=False).filter(
                                    status=True, matricula__estado_matricula__in=[2, 3]).distinct()
                            for estudiante in PerfilInscripcion.objects.filter(tienediscapacidad=True, status=True,
                                                                          persona__id__in=idpersonas):
                            #if total:
                                #campo10 = materia.id.__str__() if materia.id.__str__() else ""
                                campo1 = materia.profesor.__str__() if materia.profesor.__str__() else ""
                                campo2 = materia.profesor.persona.emailinst if materia.profesor.persona.emailinst else ""
                                campo7 = materia.profesor.persona.telefono if materia.profesor.persona.telefono else ""
                                campo3= materia.materia.asignaturamalla.malla.carrera.__str__() if materia.materia.asignaturamalla.malla.carrera.__str__() else ""
                                campo4 = materia.materia.asignatura.__str__() if materia.materia.asignatura.__str__() else ""
                                campo9 = materia.materia.paralelo.__str__() if materia.materia.paralelo.__str__() else ""
                                #for estudiante in total:
                                campo5=estudiante.__str__() if estudiante.__str__() else ""
                                campo6=estudiante.tipodiscapacidad.__str__() if estudiante.tipodiscapacidad.__str__() else ""
                                campo8 = ("%s" % estudiante.porcientodiscapacidad) +"%" if ("%s" % estudiante.porcientodiscapacidad) +"%" else ""
                                ws.write(row_num, 0, campo1, font_styl2)
                                ws.write(row_num, 1, campo2, font_styl2)
                                ws.write(row_num, 2, campo7, font_styl2)
                                ws.write(row_num, 3, campo3, font_styl2)
                                ws.write(row_num, 4, campo4, font_styl2)
                                ws.write(row_num, 5, campo9, font_styl2)
                                ws.write(row_num, 6, campo5, font_styl2)
                                ws.write(row_num, 7, campo6, font_styl2)
                                ws.write(row_num, 8, campo8, font_styl2)
                                #ws.write(row_num, 9, campo10, font_styl2)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            # TIPO DE DISCAPACIDAD
            if action == 'tipodiscapacidades':
                try:
                    data['title'] = u'Tipos de Discapacidad'
                    search = None
                    ids = None
                    tiposdiscapacidad = Discapacidad.objects.filter(status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        data['s'] = search
                        tiposdiscapacidad = tiposdiscapacidad.filter(Q(nombre__icontains=search)|Q(codigo_tthh__icontains=search))
                    paging = MiPaginador(tiposdiscapacidad, 25)

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
                    data['tiposdiscapacidad'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_verificacion_documento/discapacitados/tiposdiscapacidad.html", data)
                except Exception as e:
                    print(e)
                    pass
            if action == 'adddiscapacidad':
                form = TipoDiscapacidadForm()
                data['form'] = form
                data['action'] = action
                template = get_template("adm_verificacion_documento/discapacitados/discapacidad.html")
                return JsonResponse({"result": True, 'data': template.render(data)})
            if action == 'editdiscapacidad':
                data['id'] = id = request.GET['id']
                discapacidad = Discapacidad.objects.get(id=id)
                form = TipoDiscapacidadForm(initial={'nombre': discapacidad.nombre, 'codigo_tthh': discapacidad.codigo_tthh})
                data['form'] = form
                data['action'] = action
                template = get_template("adm_verificacion_documento/discapacitados/discapacidad.html")
                return JsonResponse({"result": True, 'data': template.render(data)})

            # SUBTIPO DE DISCAPACIDAD

            if action == 'subtipodiscapacidades':
                try:
                    data['tipo'] = tiposdiscapacidad = Discapacidad.objects.get(id=request.GET['id'])
                    data['title'] = 'Subtipos de la Discapacidad'
                    search = None
                    ids = None
                    subtiposdiscapacidad = tiposdiscapacidad.subtipodiscapacidad_set.filter(status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        data['s'] = search
                        subtiposdiscapacidad = subtiposdiscapacidad.filter(Q(nombre__icontains=search)|Q(descripcion__icontains=search))
                    paging = MiPaginador(subtiposdiscapacidad, 25)

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
                    data['subtiposdiscapacidad'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_verificacion_documento/discapacitados/subtiposdiscapacidad.html", data)
                except Exception as e:
                    print(e)
                    pass

            if action == 'addsubtipodiscapacidad':
                data['form'] = SubTipoDiscapacidadForm()
                data['action'] = action
                data['tipo'] = request.GET['tipo']
                template = get_template("adm_verificacion_documento/discapacitados/discapacidad.html")
                return JsonResponse({"result": True, 'data': template.render(data)})
            if action == 'editsubtipodiscapacidad':
                data['id'] = id = request.GET['id']
                discapacidad = SubTipoDiscapacidad.objects.get(id=id)
                form = SubTipoDiscapacidadForm(
                    initial={'nombre': discapacidad.nombre, 'descripcion': discapacidad.descripcion})
                data['form'] = form
                data['action'] = action
                template = get_template("adm_verificacion_documento/discapacitados/discapacidad.html")
                return JsonResponse({"result": True, 'data': template.render(data)})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Verificación de Documentos'
                search = None
                ids = None
                inscripcionid = None
                # cursor = connection.cursor()
                discapacitados = Inscripcion.objects.filter(matricula__status=True, matricula__nivel__periodo=periodo,
                                                           persona__perfilinscripcion__tienediscapacidad=True
                                                           )
                carreras = Carrera.objects.filter(id__in=discapacitados.values_list('carrera_id', flat=True).distinct())
                coordinacion = Coordinacion.objects.filter(id__in=discapacitados.values_list('coordinacion_id', flat=True).distinct())
                # nivel = NivelMalla.objects.filter(inscripcion_id__in=discapacitados.values_list('id', flat=True).distinct())
                if 's' in request.GET:
                    search = request.GET['s']
                    data['s'] = search
                    discapacitados = discapacitados.filter(Q(persona__nombres__icontains=search) |
                                               Q(persona__cedula__icontains=search) |
                                               Q(persona__apellido1__icontains=search) |
                                               Q(persona__apellido2__icontains=search)
                                               )
                verificacion = 0
                if 'veri' in request.GET:
                    verificacion = int(request.GET['veri'])
                    data['veri'] = verificacion
                    if verificacion > 0:
                        discapacitados = discapacitados.filter(persona__perfilinscripcion__verificadiscapacidad=int(request.GET['veri']) == 1)
                carreraselect = 0
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    data['c'] = carreraselect
                    if carreraselect > 0:
                        discapacitados = discapacitados.filter(carrera_id=carreraselect)

                modalidadselect = 0
                if 'm' in request.GET:
                    modalidadselect = int(request.GET['m'])
                    data['m'] = modalidadselect
                    if modalidadselect > 0:
                        discapacitados = discapacitados.filter(modalidad_id=modalidadselect)

                facultadselect = 0
                if 'f' in request.GET:
                    facultadselect = int(request.GET['f'])
                    data['f'] = facultadselect
                    if facultadselect > 0:
                        discapacitados = discapacitados.filter(coordinacion_id=facultadselect)
                        carreras = carreras.filter(coordinacion=facultadselect)
                discapacitados = discapacitados.order_by("persona")
                data['total'] = len(discapacitados)

                paging = MiPaginador(discapacitados, 25)


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
                data['discapacitados'] = page.object_list
                data['rango'] = len(page.object_list)
                data['facultades'] = coordinacion
                data['carreras'] = carreras
                data['carreraselect'] = carreraselect
                data['facultadselect'] = facultadselect
                data['modalidadselect'] = modalidadselect
                data['verificacion'] = verificacion
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                data['reporte_2'] = obtener_reporte('discapacitados')
                return render(request, "adm_verificacion_documento/discapacitados/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                pass #return render(request, "alu_solicitudmatricula/error.html", data)
