# -*- coding: UTF-8 -*-
import io
import os
import random
import sys

import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction, connection
from django.db.models import Q
from django.forms.models import model_to_dict
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
from med.models import Enfermedad, TipoEnfermedad
from sagest.forms import DeportistaValidacionForm, DiscapacidadValidacionForm, MigranteValidacionForm
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import SolicitudForm, PersonaEnfermedadForm, EnfermedadForm, TiposEnfermedadForm
from django.db.models.aggregates import Avg
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import RecordAcademico, SolicitudMatricula, SolicitudDetalle, Matricula, MateriaAsignada, TipoSolicitud, \
    ConfiguracionTerceraMatricula, Inscripcion, DeportistaPersona, Carrera, DisciplinaDeportiva, PerfilInscripcion, \
    MigrantePersona, PersonaEnfermedad, Persona
from sga.templatetags.sga_extras import encrypt

import urllib.parse


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    tEnfselect = []
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'savePersonaEnfermedad':
            try:
                id = int(request.POST.get('id', '0'))
                try:
                    ePersonaEnfermedad = PersonaEnfermedad.objects.get(pk=id)
                except ObjectDoesNotExist:
                    raise NameError(u"No se encontro registro de enfermedad")
                form = PersonaEnfermedadForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                ePersonaEnfermedad.estadoarchivo = form.cleaned_data['estadoarchivo']
                ePersonaEnfermedad.observacion = form.cleaned_data['observacion']
                ePersonaEnfermedad.usuariogestiona = persona.usuario
                ePersonaEnfermedad.save(request)
                log(u'Cambio de estado en gestión de enfermedad: %s' % ePersonaEnfermedad, request, 'edit')
                data['ePersona'] = ePersonaEnfermedad.persona
                template = get_template("adm_verificacion_documento/enfermedades/listEstadoEnfermedades.html")
                json_content = template.render(data)
                return JsonResponse({"result": True, 'id': ePersonaEnfermedad.persona_id, 'html': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'saveEnfermedad':
            try:
                form = EnfermedadForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                id = int(request.POST.get('id', '0'))
                try:
                    eEnfermedad = Enfermedad.objects.get(pk=id)
                    eEnfermedad.tipo = form.cleaned_data['tipo']
                    eEnfermedad.descripcion = form.cleaned_data['descripcion']
                    eEnfermedad.hereditaria = form.cleaned_data['hereditaria']
                    isNew = False
                except ObjectDoesNotExist:
                    eEnfermedad = Enfermedad(tipo=form.cleaned_data['tipo'],
                                             descripcion=form.cleaned_data['descripcion'],
                                             hereditaria=form.cleaned_data['hereditaria'])
                    isNew = True
                eEnfermedad.save(request)
                if isNew:
                    log(u'Adiciono enfermedad: %s' % eEnfermedad, request, 'add')
                else:
                    log(u'Edito enfermedad: %s' % eEnfermedad, request, 'edit')
                return JsonResponse({"result": True, 'message': "Se guardo correctamente la información"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteEnfermedad':
            try:
                id = int(request.POST.get('id', '0'))
                try:
                    deleteEnfermedad = eEnfermedad = Enfermedad.objects.get(pk=id)
                except ObjectDoesNotExist:
                    raise NameError(u"No se encontro enfermedad")
                eEnfermedad.delete()
                log(u'Elimino enfermedad: %s' % deleteEnfermedad, request, "del")
                return JsonResponse({"result": True, "mensaje": u"Se elimino correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al eliminar. %s" % ex.__str__()})

        elif action == 'saveTiposEnfermedad':
            try:
                form = TiposEnfermedadForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                id = int(request.POST.get('id', '0'))
                try:
                    etiposEnfermedades = TipoEnfermedad.objects.get(pk=id)
                    etiposEnfermedades.descripcion = form.cleaned_data['descripcion']
                    isNew = False
                except ObjectDoesNotExist:
                    etiposEnfermedades = TipoEnfermedad(
                        descripcion=form.cleaned_data['descripcion'],
                    )
                    isNew = True
                etiposEnfermedades.save(request)
                if isNew:
                    log(u'Adiciono Tipo enfermedad: %s' % etiposEnfermedades, request, 'add')
                else:
                    log(u'Tipo enfermedad: %s' % etiposEnfermedades, request, 'edit')
                return JsonResponse({"result": True, 'message': "Se guardo correctamente la información"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteTiposEnfermedad':
            try:
                id = int(request.POST.get('id', '0'))
                try:
                    deleteTiposEnfermedad = eTipoEnfermedad = TipoEnfermedad.objects.get(pk=id)
                except ObjectDoesNotExist:
                    raise NameError(u"No se encontro enfermedad")
                eTipoEnfermedad.delete()
                log(u'Elimino enfermedad: %s' % deleteTiposEnfermedad, request, "del")
                return JsonResponse({"result": True, "mensaje": u"Se elimino correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al eliminar. %s" % ex.__str__()})


        return JsonResponse({"result": False, "message": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'loadListEnfermedades':
                try:
                    id = int(request.GET.get('id', '0'))
                    ids = request.GET.get('tipoEnf', '')
                    # Decodificar y dividir la cadena en una sola línea,
                    # y convertir a enteros si hay valores, este valor se reco-
                    # del prop enviado a la plantilla
                    array_tipo_enfermedad = [int(i) for i in urllib.parse.unquote(ids).split(',')] if ids else []
                    try:
                        ePersona = Persona.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No existe persona")
                    data['ePersona'] = ePersona
                    data['tipoEnfermedadselect'] = array_tipo_enfermedad

                    template = get_template("adm_verificacion_documento/enfermedades/listEnfermedades.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"%s" % ex.__str__()})

            elif action == 'loadFormPersonaEnfermedad':
                try:
                    id = int(request.GET.get('id', '0'))
                    try:
                        ePersonaEnfermedad = PersonaEnfermedad.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro registro de enfermedad")
                    f = PersonaEnfermedadForm(initial=model_to_dict(ePersonaEnfermedad))
                    data['form'] = f
                    data['frmName'] = "frmPersonaEnfermedad"
                    data['action'] = "savePersonaEnfermedad"
                    data['ePersonaEnfermedad'] = ePersonaEnfermedad
                    template = get_template("adm_verificacion_documento/enfermedades/frmPersonaEnfermedad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormEnfermedad':
                try:
                    id = int(request.GET.get('id', '0'))
                    try:
                        eEnfermedad = Enfermedad.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        eEnfermedad = None
                    f = EnfermedadForm()
                    if eEnfermedad:
                        f.initial = model_to_dict(eEnfermedad)
                    data['form'] = f
                    data['frmName'] = "frmEnfermedad"
                    data['action'] = "saveEnfermedad"
                    data['eEnfermedad'] = eEnfermedad
                    data['id'] = eEnfermedad.id if eEnfermedad else 0
                    template = get_template("adm_verificacion_documento/enfermedades/frmEnfermedad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al obtener los datos. %s" % ex.__str__()})


            elif action == 'loadFormTiposEnfermedad':
                try:
                    id = int(request.GET.get('id', '0'))
                    try:
                        etiposEnfermedades = TipoEnfermedad.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        etiposEnfermedades = None
                    f = TiposEnfermedadForm()
                    if etiposEnfermedades:
                        f.initial = model_to_dict(etiposEnfermedades)
                    data['form'] = f
                    data['frmName'] = "frmEnfermedad"
                    data['action'] = "saveTiposEnfermedad"
                    data['etiposEnfermedades'] = etiposEnfermedades
                    data['id'] = etiposEnfermedades.id if etiposEnfermedades else 0
                    template = get_template("adm_verificacion_documento/enfermedades/frmEnfermedad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'downRptEnfermedades':
                try:
                    # nombre_archivo = "reporte_enfermedades"
                    # output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
                    # nombre = nombre_archivo + "_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"
                    # directory = os.path.join(output_folder, nombre)
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet("Hoja1")
                    fuentecabecera = workbook.add_format({
                        'align': 'center',
                        'bg_color': 'silver',
                        'border': 1,
                        'bold': 1
                    })

                    formatoceldacenter = workbook.add_format({
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'})

                    formatoceldacenter = workbook.add_format({
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'})

                    fuenteencabezado = workbook.add_format({
                        'align': 'center',
                        'bg_color': '#1C3247',
                        'font_color': 'white',
                        'border': 1,
                        'font_size': 24,
                        'bold': 1
                    })
                    columnas = [
                        (u"#", 10),
                        (u"ID Tipo", 20),
                        (u"Tipo", 20),
                        (u"ID Enfermedad", 80),
                        (u"Enfermedad", 80),
                        (u"¿Es hereditaria?", 80),
                    ]
                    ws.merge_range(0, 0, 0, columnas.__len__() - 1, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', fuenteencabezado)
                    ws.merge_range(1, 0, 1, columnas.__len__() - 1, f'REPORTE DE ENFERMEDADES', fuenteencabezado)
                    row_num, numcolum = 2, 0
                    for col_name in columnas:
                        ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                        ws.set_column(numcolum, numcolum, col_name[1])
                        numcolum += 1
                    row_num = 3
                    contador = 0
                    filtro = Q(status=True)
                    eEnfermedades = Enfermedad.objects.filter(filtro).order_by('descripcion')
                    etiposEnfermedades = TipoEnfermedad.objects.filter(filtro).order_by('descripcion')
                    for eEnfermedad in eEnfermedades:
                        contador += 1
                        ws.write(row_num, 0, contador, formatoceldacenter)
                        ws.write(row_num, 1, u"%s" % eEnfermedad.tipo_id, formatoceldacenter)
                        ws.write(row_num, 2, u"%s" % eEnfermedad.tipo.descripcion, formatoceldacenter)
                        ws.write(row_num, 3, u"%s" % eEnfermedad.id, formatoceldacenter)
                        ws.write(row_num, 4, u"%s" % eEnfermedad.descripcion, formatoceldacenter)
                        ws.write(row_num, 5, "SI" if eEnfermedad.hereditaria else "NO", formatoceldacenter)
                        row_num += 1

                    workbook.close()
                    output.seek(0)
                    # Set up the Http response.
                    filename = f'enfermedades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_verificacion_documento/enfermedad?action=viewEnfermedades&info={ex.__str__()}")

            elif action == 'viewEnfermedades':
                try:

                    data['title'] = u'Mantenimiento de enfermedades'
                    search = None
                    ids = None
                    filtro = Q(status=True)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        filtro = filtro & Q(descripcion__icontains=search)

                    tipo = 0
                    if 't' in request.GET:
                        tipo = int(request.GET.get('t', '0'))
                        if tipo > 0:
                            filtro = filtro & Q(tipo_id=tipo)
                    data['tipo'] = tipo
                    data['eTipoEnfermedades'] = eTipoEnfermedades = TipoEnfermedad.objects.filter(status=True)
                    eEnfermedades = Enfermedad.objects.filter(filtro).order_by('descripcion')

                    paging = MiPaginador(eEnfermedades, 25)

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
                    data['eEnfermedades'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_verificacion_documento/enfermedades/viewEnfermedades.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_verificacion_documento?info={ex.__str__()}")

            elif action == 'viewTiposEnfermedades':
                try:

                    data['title'] = u'Mantenimiento de Tipos Enfermedades'
                    search = None
                    ids = None
                    filtro = Q(status=True)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        filtro = filtro & Q(descripcion__icontains=search)

                    tipo = 0
                    if 't' in request.GET:
                        tipo = int(request.GET.get('t', '0'))
                        if tipo > 0:
                            filtro = filtro & Q(tipo_id=tipo)
                    data['tipo'] = tipo
                    data['eTipoEnfermedades'] = eTipoEnfermedades = TipoEnfermedad.objects.filter(status=True)
                    eTipoEnfermedades = TipoEnfermedad.objects.filter(filtro).order_by('descripcion')

                    paging = MiPaginador(eTipoEnfermedades, 25)

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
                    data['eTiposEnfermedades'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_verificacion_documento/enfermedades/viewTiposEnfermedades.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_verificacion_documento?info={ex.__str__()}")

            elif action == 'downRptAlumnosEnfermedad':
                try:
                    filtro = Q(matricula__status=True) & Q(matricula__nivel__periodo=periodo) & Q(persona__personaenfermedad__isnull=False)
                    eInscripciones = Inscripcion.objects.filter(filtro).order_by("persona__apellido1", "persona__apellido2", "persona__nombres").distinct()
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
                    ws = wb.add_sheet('Hoja1')

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Enfermedades ' + random.randint(1, 10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'REPORTE DE ENFERMEDADES', title)

                    ws.col(0).width = 10000
                    ws.col(1).width = 7000
                    ws.col(2).width = 10000
                    ws.col(3).width = 10000
                    ws.col(4).width = 10000
                    ws.col(5).width = 10000
                    ws.col(6).width = 10000
                    ws.col(7).width = 10000
                    ws.col(8).width = 10000
                    ws.col(9).width = 10000

                    row_num = 3
                    ws.write(row_num, 0, "ALUMNO", encabesado_tabla)
                    ws.write(row_num, 1, "CEDULA", encabesado_tabla)
                    ws.write(row_num, 2, "DIRECCION", encabesado_tabla)
                    ws.write(row_num, 3, u"EMAIL", encabesado_tabla)
                    ws.write(row_num, 4, u"TELEFONO", encabesado_tabla)
                    ws.write(row_num, 5, u"NIVEL", encabesado_tabla)
                    ws.write(row_num, 6, u"CARRERA", encabesado_tabla)
                    ws.write(row_num, 7, u"ENFERMEDAD", encabesado_tabla)
                    ws.write(row_num, 8, u"TIPO", encabesado_tabla)
                    ws.write(row_num, 9, u"ESTADO", encabesado_tabla)
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 4
                    for eInscripcion in eInscripciones:
                        for ePersonaEnfermedad in eInscripcion.persona.mis_enfermedades():
                            campo0 = eInscripcion.persona.nombre_completo()
                            campo1 = eInscripcion.persona.documento()
                            campo2 = eInscripcion.persona.direccion_corta()
                            campo3 = eInscripcion.persona.emailinst
                            campo4 = eInscripcion.persona.telefono
                            campo5 = eInscripcion.matricula().nivelmalla.__str__()
                            campo6 = eInscripcion.carrera.__str__()
                            campo7 = ePersonaEnfermedad.enfermedad.descripcion
                            campo8 = ePersonaEnfermedad.enfermedad.tipo.descripcion
                            campo9 = 'Pendiente'
                            if ePersonaEnfermedad.estadoarchivo:
                                if ePersonaEnfermedad.estadoarchivo == 2:
                                    campo9 = 'Validado'
                                elif ePersonaEnfermedad.estadoarchivo == 3:
                                    campo9 = 'Rechazado'
                                else:
                                    campo9 = 'Pendiente'
                            ws.write(row_num, 0, campo0, normal)
                            ws.write(row_num, 1, campo1, normal)
                            ws.write(row_num, 2, campo2, normal)
                            ws.write(row_num, 3, campo3, normal)
                            ws.write(row_num, 4, campo4, normal)
                            ws.write(row_num, 5, campo5, normal)
                            ws.write(row_num, 6, campo6, normal)
                            ws.write(row_num, 7, campo7, normal)
                            ws.write(row_num, 8, campo8, normal)
                            ws.write(row_num, 9, campo9, normal)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as e:
                    print(e)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            return JsonResponse({"result": False, "message": u"Solicitud Incorrecta."})
        else:
            try:
                data['title'] = u'Verificación de Documentos'
                search = None
                ids = None
                eTipoEnfermedad = TipoEnfermedad.objects.filter(status=True) #filtro para obtener los tipos de enfermedades
                # filtro y query para obtener los estudiantes con enfemerdades
                filtro = Q(matricula__status=True) & Q(matricula__nivel__periodo=periodo) & Q(
                    persona__personaenfermedad__isnull=False)
                eCarreras = Carrera.objects.filter(id__in=Inscripcion.objects.values_list('carrera_id', flat=True).filter(filtro).distinct())
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        filtro = filtro & Q(Q(persona__nombres__icontains=search) |
                                            Q(persona__cedula__icontains=search) |
                                            Q(persona__apellido1__icontains=search) |
                                            Q(persona__apellido2__icontains=search))
                    else:
                        filtro = filtro & Q(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))

                verificacion = 0
                if 'veri' in request.GET:
                    verificacion = int(request.GET['veri'])
                    if verificacion > 0:
                        if verificacion == 1:
                            filtro = filtro & Q(persona__personaenfermedad__estadoarchivo=2)
                        elif verificacion == 2:
                            filtro = filtro & Q(persona__personaenfermedad__estadoarchivo=3)
                        else:
                            filtro = filtro & Q(Q(persona__personaenfermedad__estadoarchivo__in=[1, 4, 5, 6]) |
                                                Q(persona__personaenfermedad__estadoarchivo__isnull=True))

                carreraselect = 0
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    if carreraselect > 0:
                        filtro = filtro & Q(carrera_id=carreraselect)

                modalidadselect = 0
                if 'm' in request.GET:
                    modalidadselect = int(request.GET['m'])
                    if modalidadselect > 0:
                        filtro = filtro & Q(modalidad_id=modalidadselect)
                eInscripciones = Inscripcion.objects.filter(filtro).order_by("persona__apellido1", "persona__apellido2", "persona__nombres").distinct()


                if 'tipEnf' in request.GET: #Este bloque recoge los ids enviados del checkbox de Tipo Enfermedad
                    try:
                        tip_enf = request.GET.get('tipEnf', '')
                        tEnfselect = [int(i) for i in tip_enf.split(',')]
                    except ValueError:
                        tEnfselect = []
                        tEnfselect = [i.id for i in eTipoEnfermedad]

                if not tEnfselect: #Inicia el valor de tipo de enfermedad como catastrofica
                    try:
                        tag_catastroficas = TipoEnfermedad.objects.get(status=True, descripcion="CATASTROFICAS")
                    except ObjectDoesNotExist:
                        tag_catastroficas = TipoEnfermedad.objects.filter(status=True).first()
                    tEnfselect.append(tag_catastroficas.id)

                filtro = filtro & Q(persona__personaenfermedad__enfermedad__tipo__in=tEnfselect) & Q(persona__personaenfermedad__status=True)

                eInscripciones = Inscripcion.objects.filter(filtro).order_by("persona__apellido1", "persona__apellido2", "persona__nombres").distinct()


                paging = MiPaginador(eInscripciones, 25)

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
                data['eInscripciones'] = page.object_list
                data['carreras'] = eCarreras
                data['carreraselect'] = carreraselect
                data['modalidadselect'] = modalidadselect
                data['etipoenfermedad'] = eTipoEnfermedad
                data['tipoEnfermedadselect'] = tEnfselect
                data['verificacion'] = verificacion
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                return render(request, "adm_verificacion_documento/enfermedades/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/adm_verificacion_documento?info={ex.__str__()}")
