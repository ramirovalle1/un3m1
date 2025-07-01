# -*- coding: UTF-8 -*-
import random
import sys

from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import json
from django.template import Context
from django.template.loader import get_template
from datetime import datetime

import xlwt
from xlwt import *

from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from sagest.forms import DeportistaValidacionForm, DiscapacidadValidacionForm, MigranteValidacionForm
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import SolicitudForm
from django.db.models.aggregates import Avg
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import RecordAcademico, SolicitudMatricula, SolicitudDetalle, Matricula, MateriaAsignada, TipoSolicitud, \
    ConfiguracionTerceraMatricula, Inscripcion, DeportistaPersona, Carrera, DisciplinaDeportiva, PerfilInscripcion, \
    MigrantePersona
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
                form = MigranteValidacionForm(request.POST)
                if form.is_valid():
                    migrante = MigrantePersona.objects.get(pk=int(request.POST['id']))
                    migrante.estadoarchivo = form.cleaned_data['estadomigrante']
                    migrante.observacion = form.cleaned_data['observacionmigrante'].strip().upper()
                    migrante.verificado = True if int(form.cleaned_data['estadomigrante']) == 2 else False
                    migrante.save(request)
                    log(u'Actualizó registro de Migrante: %s' % migrante, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'datos':
                try:
                    migrante = MigrantePersona.objects.get(pk=int(request.GET['id']))
                    data['migrante'] = migrante
                    form = MigranteValidacionForm(initial={
                        'estadomigrante':migrante.estadoarchivo,
                        'observacionmigrante':migrante.observacion,
                    })
                    form.editar()
                    form.fields['estadomigrante'].choices= (
                                ('', u'--Seleccione--'),
                                (2, u'VALIDADO'),
                                (3, u'RECHAZADO'),
                                (5, u'REVISIÓN'),
                                (6, u'RECHAZADO IO')
                    )

                    data['form'] = form
                    template = get_template("adm_verificacion_documento/migrantes/datos.html")
                    return JsonResponse({"result": True, 'datos': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': u'Error al obtener los datos'})
            elif action == 'reporte':
                try:
                    migrantes = Inscripcion.objects.filter(
                        matricula__status=True, matricula__nivel__periodo=periodo,
                        persona__migrantepersona__isnull=False,
                        persona__migrantepersona__status=True
                    )
                    if 's' in request.GET:
                        search = request.GET['s']
                        migrantes = migrantes.filter(Q(persona__nombres__icontains=search) |
                                                     Q(persona__cedula__icontains=search) |
                                                     Q(persona__apellido1__icontains=search) |
                                                     Q(persona__apellido2__icontains=search))
                    if 'veri' in request.GET:
                        verificacion = int(request.GET['veri'])
                        if verificacion > 0:
                            migrantes = migrantes.filter(persona__migrantepersona__verificado=int(request.GET['veri']) == 1)
                    if 'c' in request.GET:
                        carreraselect = int(request.GET['c'])
                        if carreraselect > 0:
                            migrantes = migrantes.filter(carrera_id=carreraselect)
                    if 'm' in request.GET:
                        modalidadselect = int(request.GET['m'])
                        if modalidadselect > 0:
                            migrantes = migrantes.filter(modalidad_id=modalidadselect)

                    migrantes = migrantes.order_by("persona")
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
                    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                    encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
                    normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
                    subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
                    normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    normal.borders = borders
                    normalc.borders = borders
                    normalsub.borders = borders
                    subtema.borders = borders
                    encabesado_tabla.borders = borders
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Migrantes ' + random.randint(1,
                                                                                                    10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'REPORTE DE MIGRANTES', title)

                    ws.col(0).width = 10000
                    ws.col(1).width = 7000
                    ws.col(2).width = 10000
                    ws.col(3).width = 10000
                    ws.col(4).width = 10000
                    ws.col(5).width = 10000
                    ws.col(6).width = 10000
                    ws.col(7).width = 10000
                    ws.col(8).width = 10000

                    row_num = 3
                    ws.write(row_num, 0, "ALUMNO", encabesado_tabla)
                    ws.write(row_num, 1, "CEDULA", encabesado_tabla)
                    ws.write(row_num, 2, "DIRECCION", encabesado_tabla)
                    ws.write(row_num, 3, u"EMAIL", encabesado_tabla)
                    ws.write(row_num, 4, u"TELEFONO", encabesado_tabla)
                    ws.write(row_num, 5, u"NIVEL", encabesado_tabla)
                    ws.write(row_num, 6, u"CARRERA", encabesado_tabla)
                    ws.write(row_num, 7, u"PAIS", encabesado_tabla)
                    ws.write(row_num, 8, u"ESTADO VALIDACION", encabesado_tabla)
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 4
                    for migrante in migrantes:
                        campo0 = migrante.persona.nombre_completo()
                        campo1 = migrante.persona.cedula
                        campo2 = migrante.persona.direccion
                        campo3 = migrante.persona.emailinst
                        campo4 = migrante.persona.telefono
                        campo5 = migrante.matricula().nivelmalla.__str__()
                        campo6 = migrante.carrera.__str__()
                        campo7 = migrante.persona.pais.__str__()
                        campo8 = migrante.persona.registro_migrante().get_estadoarchivo_display()

                        ws.write(row_num, 0, campo0, normal)
                        ws.write(row_num, 1, campo1, normal)
                        ws.write(row_num, 2, campo2, normal)
                        ws.write(row_num, 3, campo3, normal)
                        ws.write(row_num, 4, campo4, normal)
                        ws.write(row_num, 5, campo5, normal)
                        ws.write(row_num, 6, campo6, normal)
                        ws.write(row_num, 7, campo7, normal)
                        ws.write(row_num, 8, campo8, normal)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as e:
                    print(e)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Verificación de Documentos'
                search = None
                ids = None
                inscripcionid = None
                # cursor = connection.cursor()
                migrantes = Inscripcion.objects.filter(
                    matricula__status=True, matricula__nivel__periodo=periodo,
                    persona__migrantepersona__isnull=False,
                    persona__migrantepersona__status=True
                                                           )
                carreras = Carrera.objects.filter(id__in=migrantes.values_list('carrera_id', flat=True).distinct())
                if 's' in request.GET:
                    search = request.GET['s']
                    migrantes = migrantes.filter(Q(persona__nombres__icontains=search) |
                                               Q(persona__cedula__icontains=search) |
                                               Q(persona__apellido1__icontains=search) |
                                               Q(persona__apellido2__icontains=search)
                                               )
                verificacion = 0
                if 'veri' in request.GET:
                    verificacion = int(request.GET['veri'])
                    if verificacion > 0:
                        migrantes = migrantes.filter(persona__migrantepersona__verificado=int(request.GET['veri']) == 1)

                carreraselect = 0
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    if carreraselect > 0:
                        migrantes = migrantes.filter(carrera_id=carreraselect)

                modalidadselect = 0
                if 'm' in request.GET:
                    modalidadselect = int(request.GET['m'])
                    if modalidadselect > 0:
                        migrantes = migrantes.filter(modalidad_id=modalidadselect)

                migrantes = migrantes.order_by("persona")

                paging = MiPaginador(migrantes, 25)

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
                data['migrantes'] = page.object_list
                data['carreras'] = carreras
                data['carreraselect'] = carreraselect
                data['modalidadselect'] = modalidadselect
                data['verificacion'] = verificacion
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                data['reporte_2'] = obtener_reporte('discapacitados')
                return render(request, "adm_verificacion_documento/migrantes/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                pass #return render(request, "alu_solicitudmatricula/error.html", data)
