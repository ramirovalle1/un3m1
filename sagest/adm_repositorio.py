# -*- coding: UTF-8 -*-
import json
import sys
from itertools import chain
import random
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.template import Context
from xlwt import easyxf, XFStyle
from xlwt import *

from balcon.models import Informacion, Proceso, Solicitud, Agente, Servicio, HistorialSolicitud, ProcesoServicio, \
    RequisitosConfiguracion, RequisitosSolicitud, Categoria
from decorators import secure_module, last_access
from even.models import PeriodoEvento, RegistroEvento, DetallePeriodoEvento
from sagest.forms import CarpetaForm, CarpetaArchivoForm, ConfigCarpetaForm, EditCarpetaArchivoForm, CompartirCarpetaForm
from sagest.models import Carpeta, ArchivoCarpeta, ConfiguracionCarpeta, CarpetaCompartida

from sga.commonviews import adduserdata
from sga.funciones import log
from django.db import connections

from sga.models import Administrativo
from sga.templatetags.sga_extras import encrypt
from sga.funcionesxhtml2pdf import conviert_html_to_pdf

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addcarpeta':
            try:
                # if int(request.POST['cantidadarchivos']) == 0:
                #     return JsonResponse({"result": True, "mensaje": u"Cantidad de archivos debe ser mayor a 0"})
                f = CarpetaForm(request.POST)
                if f.is_valid():
                    if request.POST['id']:
                        carpeta = Carpeta(nombre=f.cleaned_data['nombre'],
                                          persona_id=persona.id,
                                          carpetaref_id=request.POST['id'],
                                          cantidadarchivos=f.cleaned_data['cantidadarchivos']
                                          )
                        carpeta.save(request)
                    else:
                        carpeta = Carpeta(nombre=f.cleaned_data['nombre'],
                                          persona_id=persona.id,
                                          carpetaref_id=None,
                                          cantidadarchivos=f.cleaned_data['cantidadarchivos']
                                          )
                        carpeta.save(request)
                    log(u'Adiciono nuevo carpeta: %s' % carpeta, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        if action == 'compartircarpeta':
            try:
                carpeta = Carpeta.objects.get(pk=request.POST['id'])
                f = CompartirCarpetaForm(request.POST)
                if f.is_valid():
                    if 'persona_sel' in request.POST:
                        administrativo = Administrativo.objects.get(pk=request.POST['persona_sel'])
                        persona = administrativo.persona_id
                        for carp in carpeta.carpetashijas():

                            if CarpetaCompartida.objects.filter(status=True, carpeta_id=carp, persona_id=persona).exists():
                                cc = CarpetaCompartida.objects.get(status=True, carpeta_id=carp, persona_id=persona)
                                if not cc.puedeeditar:
                                    cc.puedeeditar = True
                                    cc.save(request)
                                elif cc.puedeeditar:
                                    cc.puedeeditar =False
                                    cc.save(request)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"La carpeta ya fue compartida con el usuario seleccionado."})
                            else:
                                carpetacompartida = CarpetaCompartida(carpeta_id=carp,
                                                                      persona_id=persona,
                                                                      puedeeditar=f.cleaned_data['editar']
                                                                      )
                                carpetacompartida.save(request)
                                log(u'Adiciono nuevo carpeta: %s' % carpetacompartida, request, "add")

                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'editcarpeta':
            try:
                f = CarpetaForm(request.POST)
                if f.is_valid():
                    carpeta = Carpeta.objects.get(pk=request.POST['id'])
                    carpeta.nombre = f.cleaned_data['nombre']
                    carpeta.cantidadarchivos = f.cleaned_data['cantidadarchivos']
                    carpeta.save(request)
                    log(u'Modifico carpeta: %s' % carpeta, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'configcarpeta':
            try:
                f = ConfigCarpetaForm(request.POST)
                if f.is_valid():
                    confcarpeta = ConfiguracionCarpeta.objects.get(pk=request.POST['id'])
                    confcarpeta.cantidad = f.cleaned_data['cantidad']
                    confcarpeta.save(request)
                    log(u'Modifico confirguracion carpeta: %s' % confcarpeta, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'reportea':
            try:
                __author__ = 'Unemi'
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet("HOJA1", cell_overwrite_ok=True)
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=reportes' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"NOMBRE CARPETA", 9000),
                    (u"ARCHIVOS CARGADOS", 6000),
                    (u"TOTAL ARCHIVOS POR CARGAR", 6000),
                    (u"PORCENTAJE DE CARGA", 6000),
                ]
                row_num = 2
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 3
                i = 0
                carpetas = persona.carpeta_set.filter(status=True, carpetaref_id__isnull=True).distinct()

                for carpeta in carpetas:
                    campo2 = str(carpeta.nombre)
                    campo3 = str(carpeta.archivos())
                    campo4 = str(carpeta.cantidadarchivos)
                    campo5 = str(carpeta.porcentajearchivos())+'%'

                    ws.write(row_num, 0, campo2, font_style2)
                    ws.write(row_num, 1, campo3, font_style2)
                    ws.write(row_num, 2, campo4, font_style2)
                    ws.write(row_num, 3, campo5, font_style2)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'editarchivo':
            try:
                f = EditCarpetaArchivoForm(request.POST)
                if f.is_valid():
                    archivo = ArchivoCarpeta.objects.get(pk=request.POST['id'])
                    archivo.nombre = f.cleaned_data['nombre']
                    archivo.save(request)
                    log(u'Modifico archivo: %s' % archivo, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'cargararchivo':
            try:
                carpeta = Carpeta.objects.get(pk=request.POST['id'])

                # if carpeta.archivos() == carpeta.cantidadarchivos:
                #     return JsonResponse({"result": "bad", "mensaje": u"Ha completado el 100% de carga de archivos."})
                # else:
                f = CarpetaArchivoForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if d.size > 209715200:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 165 Mb."})

                    if f.is_valid():
                        if f.cleaned_data['tipoarchivo'] == '1':
                            if ext == '.doc' or ext == '.docx':
                                a = 1
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .doc, .docx"})

                        elif f.cleaned_data['tipoarchivo'] == '2':
                            if ext == '.xls' or ext == '.xlsx':
                                a = 1
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .xlsx, .xls"})

                        elif f.cleaned_data['tipoarchivo'] == '3':
                            if ext == '.ppt' or ext == '.pptx':
                                a = 1
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .ppt, .pptx"})

                        elif f.cleaned_data['tipoarchivo'] == '4':
                            if ext == '.pdf' or ext == '.PDF':
                                a = 1
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .PDF, .pdf"})

                        elif f.cleaned_data['tipoarchivo'] == '5':
                            if ext == '.zip':
                                a = 1
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .rar"})
                        if d.size > 209715200:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 200 Mb."})

                        if f.is_valid():
                            archivoc = ArchivoCarpeta(nombre=f.cleaned_data['nombre'],
                                                      tipoarchivo=f.cleaned_data['tipoarchivo'],
                                                      carpeta_id=request.POST['id'])
                            archivoc.save(request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                archivoc.archivo = newfile
                                archivoc.save(request)

                            log(u'Adiciono nuevo archivo: %s' % archivoc, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'delcarpeta':
            try:
                carpeta = Carpeta.objects.get(pk=request.POST['id'])
                if carpeta.en_uso():
                    return JsonResponse({"resp": False, "message": u"La carpeta contiene archivos o carpetas cargadas, si desea eliminarla,"
                                                                   u"por favor elimine primero su contenido."}, safe=False)
                else:
                    carpeta.status = False
                    carpeta.save()
                    log(u'Elimino carpeta: %s' % carpeta, request, "del")
                    return JsonResponse({"resp": True}, safe=False)
            except Exception as ex:
                return JsonResponse({"resp": False, "message": "Error: {}".format(ex)}, safe=False)

        elif action == 'delarchivo':
            try:
                archivo = ArchivoCarpeta.objects.get(pk=request.POST['id'])
                archivo.status = False
                archivo.save()
                log(u'Elimino archivo: %s' % archivo, request, "del")
                return JsonResponse({"resp": True}, safe=False)
            except Exception as ex:
                return JsonResponse({"resp": False, "message": "Error: {}".format(ex)}, safe=False)

        #
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addcarpeta':
                try:
                    if request.GET['id']:
                        data['carpeta'] = carpeta = Carpeta.objects.get(pk=int(request.GET['id']))
                    data['form'] = CarpetaForm()
                    template = get_template("adm_repositorio/modal_addcarpeta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

            elif action == 'editcarpeta':
                try:
                    data['carpeta'] = carpeta = Carpeta.objects.get(pk=request.GET['id'])
                    data['form'] = CarpetaForm(initial=model_to_dict(carpeta))
                    template = get_template("adm_repositorio/modal_editcarpeta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. {}".format(str(ex))})


            elif action == 'compartircarpeta':
                try:
                    data['carpeta'] = carpeta = Carpeta.objects.get(pk=request.GET['id'])
                    data['carpetacompartida'] = carpetac = CarpetaCompartida.objects.filter(carpeta_id=carpeta)
                    data['form'] = CompartirCarpetaForm()
                    template = get_template("adm_repositorio/modal_compartircarpeta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

            elif action == 'buscaradministrativo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # elif action == 'configcarpeta':
            #     try:
            #         carpeta = Carpeta.objects.get(pk=request.GET['id'])
            #         data['configcarpeta'] = configcarpeta = ConfiguracionCarpeta.objects.get(carpeta_id=carpeta)
            #         data['form'] = ConfigCarpetaForm(initial=model_to_dict(configcarpeta))
            #         template = get_template("adm_repositorio/modal_configcarpeta.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         pass

            elif action == 'editarchivo':
                try:
                    data['archivo'] = archivo = ArchivoCarpeta.objects.get(pk=request.GET['id'])
                    data['form'] = EditCarpetaArchivoForm(initial=model_to_dict(archivo))
                    template = get_template("adm_repositorio/modal_editarchivo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

            elif action == 'cargararchivo':
                try:
                    data['carpeta'] = carpeta = Carpeta.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = CarpetaArchivoForm()
                    template = get_template("adm_repositorio/modal_cargararchivo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

            # elif action == 'reporte_avancecarpeta':
            #     try:
            #         data['carpetas'] = Carpeta.objects.filter(status=True)
            #         return conviert_html_to_pdf(
            #             'adm_repositorio/reportepdf.html',
            #             {
            #                 'pagesize': 'A4',
            #                 'data': data,
            #             }
            #         )
            #     except Exception as ex:
            #         pass

            elif action == 'carpeta':
                try:
                    data['carpeta'] = carpeta = Carpeta.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['title'] = 'CARPETA {}'.format(carpeta.nombre.upper())
                    data['carpetas'] = carpetas = Carpeta.objects.filter(carpetaref=int(encrypt(request.GET['id'])), status=True).exclude(pk=carpeta.id)
                    data['archivos'] = archivos = ArchivoCarpeta.objects.filter(carpeta_id=carpeta, status=True)
                    return render(request, "adm_repositorio/carpetas.html", data)
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. {}".format(str(ex))})

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

        else:
            try:
                data['title'] = u'Repositorio de Archivos'
                data['carpetas'] = carpetas = persona.carpeta_set.filter(status=True, carpetaref_id__isnull=True).distinct()
                listaidscarpeta = []
                data['carpetascompartidas'] = carpetascompartidas = persona.carpetacompartida_set.filter(status=True, carpeta__carpetaref_id__isnull=True).distinct().values_list('carpeta_id', flat=True)
                listaidscarpeta += carpetascompartidas
                data['ccompartidas'] = ccompartidas = Carpeta.objects.filter(status=True, pk__in= listaidscarpeta )
                paging = Paginator(carpetas, 30)
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
                return render(request, "adm_repositorio/view.html", data)
            except Exception as ex:
                pass
