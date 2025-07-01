# -*- coding: UTF-8 -*-

from decimal import Decimal
import xlrd
from googletrans import Translator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import AnexoRecursoForm
from sagest.models import AnexoRecurso, datetime, UnidadMedidaPresupuesto
from settings import ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata
from sga.forms import ImportarArchivoMaterialesXLSForm, ImportarArchivoSalariosXLSForm, \
    ImportarArchivoMaquinariasXLSForm
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import Archivo


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = AnexoRecursoForm(request.POST)
                if f.is_valid():
                    anexo = AnexoRecurso(tipoanexo=f.cleaned_data['tipoanexo'],
                                         descripcion=f.cleaned_data['descripcion'],
                                         unidadmedida=f.cleaned_data['unidadmedida'],
                                         costomaquinaria=f.cleaned_data['costomaquinaria'],
                                         costosalario=f.cleaned_data['costosalario'],
                                         costomateriale=f.cleaned_data['costomateriale'])
                    anexo.save(request)
                    log(u'Adiciono un nuevo anexo: %s' % anexo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'edit':
            try:
                anexo = AnexoRecurso.objects.get(pk=request.POST['id'])
                f = AnexoRecursoForm(request.POST)
                if f.is_valid():
                    anexo.tipoanexo = f.cleaned_data['tipoanexo']
                    anexo.descripcion = f.cleaned_data['descripcion']
                    anexo.unidadmedida = f.cleaned_data['unidadmedida']
                    anexo.costomaquinaria = f.cleaned_data['costomaquinaria']
                    anexo.costosalario = f.cleaned_data['costosalario']
                    anexo.costomateriale = f.cleaned_data['costomateriale']
                    anexo.save(request)
                    log(u'Modifico anexo: %s' % anexo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje":translator.translate(ex.__str__(),'es').text})

        if action == 'delete':
            try:
                anexo = AnexoRecurso.objects.get(pk=request.POST['id'])
                log(u'Elimino anexo: %s' % anexo, request, "del")
                anexo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'importarmateriales':
            try:
                form = ImportarArchivoMaterialesXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION ANEXO MATERIALES',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save()
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea >= 2:
                            cols = sheet.row_values(rowx)
                            # UNIDAD DE MEDIDA, INSERTAR O ASIGNAR
                            unidadmedida = None
                            if not UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper()).exists():
                                unidadmedida = UnidadMedidaPresupuesto(descripcion=cols[1].strip())
                                unidadmedida.save(request)
                            else:
                                unidadmedida = UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper())[0]
                            # VALIDACION DEL COSTO
                            costomateriale = 0
                            if cols[2] != '':
                                costomateriale = float(cols[2])
                            if not AnexoRecurso.objects.filter(tipoanexo=4, descripcion=cols[0].strip().upper(), unidadmedida=unidadmedida).exists():
                                anexo = AnexoRecurso(tipoanexo=4,
                                                     descripcion=cols[0].strip().upper(),
                                                     unidadmedida=unidadmedida,
                                                     costomateriale=costomateriale)
                                anexo.save(request)
                            else:
                                anexo = AnexoRecurso.objects.filter(tipoanexo=4, descripcion=cols[0].strip().upper(), unidadmedida=unidadmedida)[0]
                                anexo.costomateriale = Decimal(cols[2])
                                anexo.save(request)
                        linea += 1
                    log(u'Importo anexos materiales obras', request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'importarmaquinaria':
            try:
                form = ImportarArchivoMaquinariasXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION ANEXOS EQUIPO',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea >= 2:
                            cols = sheet.row_values(rowx)
                            # unidad de medida, insertar o asignar
                            unidadmedida = None
                            if not UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper()).exists():
                                unidadmedida = UnidadMedidaPresupuesto(descripcion=cols[1].strip())
                                unidadmedida.save(request)
                            else:
                                unidadmedida = UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper())[0]
                            # VALIDACION DEL COSTO
                            costomateriale = 0
                            if cols[2] != '':
                                costomateriale = float(cols[2])
                            if not AnexoRecurso.objects.filter(tipoanexo=2, descripcion=cols[0].strip().upper(), unidadmedida=unidadmedida).exists():
                                anexo = AnexoRecurso(tipoanexo=2,
                                                     descripcion=cols[0].strip().upper(),
                                                     unidadmedida=unidadmedida,
                                                     costomaquinaria=costomateriale)
                                anexo.save(request)
                            else:
                                anexo = AnexoRecurso.objects.filter(tipoanexo=2, descripcion=cols[0].strip().upper(), unidadmedida=unidadmedida)[0]
                                anexo.costomaquinaria = float(cols[2])
                                anexo.save(request)
                        linea += 1
                    log(u'Importo anexo equipo', request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'importarsalarios':
            try:
                form = ImportarArchivoSalariosXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION ANEXOS MANOS DE OBRAS',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea >= 2:
                            cols = sheet.row_values(rowx)
                            # VALIDACION DEL COSTO
                            costomateriale = 0
                            if cols[1] != '':
                                costomateriale = float(cols[1])
                            if not AnexoRecurso.objects.filter(tipoanexo=3, descripcion=cols[0].strip().upper()).exists():
                                anexo = AnexoRecurso(tipoanexo=3,
                                                     descripcion=cols[0].strip().upper(),
                                                     costosalario=costomateriale)
                                anexo.save(request)
                            else:
                                anexo = AnexoRecurso.objects.filter(tipoanexo=3, descripcion=cols[0].strip().upper())[0]
                                anexo.costosalario = costomateriale
                                anexo.save(request)
                        linea += 1
                    log(u'Importo anexos manos de obras obras', request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Anexo de Recurso'
                    data['form'] = AnexoRecursoForm()
                    return render(request, 'ob_anexosrecursos/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Anexos de Recursos'
                    data['anexo'] = anexo = AnexoRecurso.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(anexo)
                    data['form'] = AnexoRecursoForm(initial=initial)
                    return render(request, 'ob_anexosrecursos/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Anexos de Recursos'
                    data['anexo'] = AnexoRecurso.objects.get(pk=request.GET['id'])
                    return render(request, 'ob_anexosrecursos/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'importarmateriales':
                try:
                    data['title'] = u'Importar Materiales'
                    data['form'] = ImportarArchivoMaterialesXLSForm()
                    return render(request, "ob_anexosrecursos/importarmateriales.html", data)
                except Exception as ex:
                    pass

            if action == 'importarsalarios':
                try:
                    data['title'] = u'Importar Mano de Obra'
                    data['form'] = ImportarArchivoSalariosXLSForm()
                    return render(request, "ob_anexosrecursos/importarsalarios.html", data)
                except Exception as ex:
                    pass

            if action == 'importarmaquinaria':
                try:
                    data['title'] = u'Importar Equipo'
                    data['form'] = ImportarArchivoMaquinariasXLSForm()
                    return render(request, "ob_anexosrecursos/importarmaquinaria.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Anexos de Recursos'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                anexos = AnexoRecurso.objects.filter(descripcion__icontains=search, status=True)
            elif 'id' in request.GET:
                ids = request.GET['id']
                anexos = AnexoRecurso.objects.filter(id=ids)
            else:
                anexos = AnexoRecurso.objects.filter(status=True)
            paging = MiPaginador(anexos, 25)
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
            data['anexos'] = page.object_list
            return render(request, "ob_anexosrecursos/view.html", data)