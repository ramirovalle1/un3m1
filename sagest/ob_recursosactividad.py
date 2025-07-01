# -*- coding: UTF-8 -*-

from decimal import Decimal
import xlrd
from googletrans import Translator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import NomencladorPresupuestoForm, DetalleNomencladorForm
from sagest.models import NomencladorPresupuesto, DetalleNomenclador, datetime, UnidadMedidaPresupuesto
from settings import ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata
from sga.forms import ImportarArchivoRecursosMaterialesXLSForm, ImportarArchivoRecursosSalariosXLSForm, \
    ImportarArchivoRecursosMaquinariasXLSForm
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
                f = NomencladorPresupuestoForm(request.POST)
                if f.is_valid():
                    recurso = NomencladorPresupuesto(unidadmedida=f.cleaned_data['unidadmedida'],
                                                     descripcion=f.cleaned_data['descripcion'])
                    recurso.save(request)
                    log(u'Adiciono un nuevo recurso: %s' % recurso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'edit':
            try:
                recurso = NomencladorPresupuesto.objects.get(pk=request.POST['id'])
                f = NomencladorPresupuestoForm(request.POST)
                if f.is_valid():
                    recurso.descripcion = f.cleaned_data['descripcion']
                    recurso.unidadmedida = f.cleaned_data['unidadmedida']
                    recurso.save(request)
                    log(u'Modifico recurso: %s' % recurso, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje": translator.translate(ex.__str__(),'es').text})

        if action == 'delete':
            try:
                recurso = NomencladorPresupuesto.objects.get(pk=request.POST['id'])
                log(u'Elimino recurso: %s' % recurso, request, "del")
                recurso.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'adddetallerecurso':
            try:
                f = DetalleNomencladorForm(request.POST)
                if f.is_valid():
                    recurso = NomencladorPresupuesto.objects.get(pk=request.POST['id'])
                    costohorareferencia = 0
                    if f.cleaned_data['tiporecurso'] == '2':
                        costohorareferencia = Decimal(f.cleaned_data['cantidadreferencia'] * f.cleaned_data['tarifareferencia']).quantize(Decimal('.0001'))
                    if f.cleaned_data['tiporecurso'] == '3':
                        costohorareferencia = Decimal(f.cleaned_data['cantidadreferencia'] * f.cleaned_data['jornadareferencia']).quantize(Decimal('.0001'))
                    rendimiento = Decimal(f.cleaned_data['rendimientoreferencia']).quantize(Decimal('.0001'))
                    otroindirecto = Decimal(f.cleaned_data['otroindirecto']).quantize(Decimal('.0001'))
                    costoreferencia = Decimal((costohorareferencia * rendimiento) + otroindirecto).quantize(Decimal('.0001'))
                    if f.cleaned_data['tiporecurso'] == '4':
                        costoreferencia = Decimal((f.cleaned_data['cantidadreferencia'] * f.cleaned_data['preciomaterialunitario']) + otroindirecto).quantize(Decimal('.0001'))
                    if f.cleaned_data['tiporecurso'] == '5':
                        costoreferencia = Decimal((f.cleaned_data['cantidadreferencia'] * f.cleaned_data['tarifareferencia']) + otroindirecto).quantize(Decimal('.0001'))
                    detallerecurso = DetalleNomenclador(nomencladorpresupuesto=recurso,
                                                        tiporecurso=f.cleaned_data['tiporecurso'],
                                                        descripcion=f.cleaned_data['descripcion'],
                                                        unidadmedida=f.cleaned_data['unidadmedida'],
                                                        cantidadreferencia=f.cleaned_data['cantidadreferencia'],
                                                        preciomaterialunitario=f.cleaned_data['preciomaterialunitario'],
                                                        tarifareferencia=f.cleaned_data['tarifareferencia'],
                                                        jornadareferencia=f.cleaned_data['jornadareferencia'],
                                                        costohorareferencia=costohorareferencia,
                                                        rendimientoreferencia=f.cleaned_data['rendimientoreferencia'],
                                                        otroindirecto=f.cleaned_data['otroindirecto'],
                                                        costoreferencia=costoreferencia)
                    detallerecurso.save(request)
                    recurso.actualizar_recurso()
                    log(u'Adiciono un nuevo detalle de recurso: %s' % recurso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'editdetallerecurso':
            try:
                detallerecurso = DetalleNomenclador.objects.get(pk=request.POST['id'])
                recurso = detallerecurso.nomencladorpresupuesto
                f = DetalleNomencladorForm(request.POST)
                if f.is_valid():
                    cantidad = Decimal(f.cleaned_data['cantidadreferencia']).quantize(Decimal('.01'))
                    preciou = Decimal(f.cleaned_data['preciomaterialunitario']).quantize(Decimal('.01'))
                    tarifa = Decimal(f.cleaned_data['tarifareferencia']).quantize(Decimal('.0001'))
                    jornal = Decimal(f.cleaned_data['jornadareferencia']).quantize(Decimal('.0001'))
                    rendimiento = Decimal(f.cleaned_data['rendimientoreferencia']).quantize(Decimal('.0001'))
                    costohorareferencia = 0
                    costoreferencia = 0
                    if f.cleaned_data['tiporecurso'] == '2':
                        costohorareferencia = Decimal(cantidad * tarifa).quantize(Decimal('.0001'))
                        costoreferencia = Decimal(costohorareferencia * rendimiento).quantize(Decimal('.0001'))
                    if f.cleaned_data['tiporecurso'] == '3':
                        costohorareferencia = Decimal(cantidad * jornal).quantize(Decimal('.0001'))
                        costoreferencia = Decimal(costohorareferencia * rendimiento).quantize(Decimal('.0001'))
                    if f.cleaned_data['tiporecurso'] == '4':
                        costoreferencia = Decimal(cantidad * preciou).quantize(Decimal('.0001'))
                    if f.cleaned_data['tiporecurso'] == '5':
                        costoreferencia = Decimal(cantidad * tarifa).quantize(Decimal('.0001'))
                    detallerecurso.tiporecurso = f.cleaned_data['tiporecurso']
                    detallerecurso.descripcion = f.cleaned_data['descripcion']
                    detallerecurso.unidadmedida = f.cleaned_data['unidadmedida']
                    detallerecurso.cantidadreferencia = cantidad
                    detallerecurso.preciomaterialunitario = preciou
                    detallerecurso.tarifareferencia = tarifa
                    detallerecurso.jornadareferencia = jornal
                    detallerecurso.costohorareferencia = costohorareferencia
                    detallerecurso.rendimientoreferencia = rendimiento
                    detallerecurso.otroindirecto = f.cleaned_data['otroindirecto']
                    detallerecurso.costoreferencia = costoreferencia
                    detallerecurso.save(request)
                    recurso.actualizar_recurso()
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje": translator.translate(ex.__str__(),'es').text})

        if action == 'deletedetallerecurso':
            try:
                detallerecurso = DetalleNomenclador.objects.get(pk=request.POST['id'])
                recurso = detallerecurso.nomencladorpresupuesto
                log(u'Elimino recurso: %s' % detallerecurso, request, "del")
                detallerecurso.delete()
                recurso.actualizar_recurso()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'importarmateriales':
            try:
                form = ImportarArchivoRecursosMaterialesXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION ANEXO MATERIALES',
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
                            if int(cols[0]) == 1:
                                # RECURSOS MATERIAL INSERTAR
                                unidadmedida = None
                                if not UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper()).exists():
                                    unidadmedida = UnidadMedidaPresupuesto(descripcion=cols[1].strip())
                                    unidadmedida.save(request)
                                else:
                                    unidadmedida = UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper())[0]
                                nomencladorpresupuesto = None
                                if not NomencladorPresupuesto.objects.filter(unidadmedida=unidadmedida, descripcion=cols[2].strip().upper()).exists():
                                    nomencladorpresupuesto = NomencladorPresupuesto(unidadmedida=unidadmedida,
                                                                                    descripcion=cols[2].strip().upper())
                                    nomencladorpresupuesto.save(request)
                                else:
                                    nomencladorpresupuesto = NomencladorPresupuesto.objects.filter(unidadmedida=unidadmedida, descripcion=cols[2].strip().upper())[0]
                            if int(cols[0]) == 2:
                                # ANEXO DEL RECURSO INSERTAR
                                costoreferencia = Decimal(cols[3] * cols[4]).quantize(Decimal('.0001'))
                                if not DetalleNomenclador.objects.filter(nomencladorpresupuesto=nomencladorpresupuesto, tiporecurso=4, descripcion=cols[2].strip().upper(), unidadmedida=unidadmedida).exists():
                                    detallerecurso = DetalleNomenclador(nomencladorpresupuesto=nomencladorpresupuesto,
                                                                        tiporecurso=4,
                                                                        descripcion=cols[2].strip().upper(),
                                                                        unidadmedida=unidadmedida,
                                                                        cantidadreferencia=cols[3],
                                                                        preciomaterialunitario=cols[4],
                                                                        tarifareferencia=0,
                                                                        jornadareferencia=0,
                                                                        costohorareferencia=0,
                                                                        rendimientoreferencia=0,
                                                                        costoreferencia=costoreferencia,
                                                                        otroindirecto=cols[5])
                                    detallerecurso.save(request)
                                else:
                                    detallerecurso = DetalleNomenclador.objects.filter(nomencladorpresupuesto=nomencladorpresupuesto, tiporecurso=4, descripcion=cols[2].strip().upper(), unidadmedida=unidadmedida)[0]
                                    detallerecurso.cantidadreferencia = cols[3]
                                    detallerecurso.preciomaterialunitario = cols[4]
                                    detallerecurso.tarifareferencia = 0
                                    detallerecurso.jornadareferencia = 0
                                    detallerecurso.costohorareferencia = 0
                                    detallerecurso.rendimientoreferencia = 0
                                    detallerecurso.costoreferencia = costoreferencia
                                    detallerecurso.otroindirecto = cols[5]
                                    detallerecurso.save(request)
                                nomencladorpresupuesto.actualizar_recurso()
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
                form = ImportarArchivoRecursosMaquinariasXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION ANEXOS EQUIPO',
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
                            if int(cols[0]) == 1:
                                # RECURSOS equipos insertar
                                unidadmedida = None
                                if not UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper()).exists():
                                    unidadmedida = UnidadMedidaPresupuesto(descripcion=cols[1].strip())
                                    unidadmedida.save(request)
                                else:
                                    unidadmedida = UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper())[0]

                                nomencladorpresupuesto = None
                                if not NomencladorPresupuesto.objects.filter(unidadmedida=unidadmedida, descripcion=cols[2].strip().upper()).exists():
                                    nomencladorpresupuesto = NomencladorPresupuesto(unidadmedida=unidadmedida,
                                                                                    descripcion=cols[2].strip().upper())
                                    nomencladorpresupuesto.save(request)
                                else:
                                    nomencladorpresupuesto = NomencladorPresupuesto.objects.filter(unidadmedida=unidadmedida, descripcion=cols[2].strip().upper())[0]

                            if int(cols[0]) == 2:
                                # ANEXO DEL RECURSO equipo insertar
                                costohorareferencia = Decimal(cols[4] * cols[5]).quantize(Decimal('.0001'))
                                rendimiento = Decimal(cols[3]).quantize(Decimal('.0001'))
                                costoreferencia = Decimal(costohorareferencia * rendimiento).quantize(Decimal('.0001'))
                                if not DetalleNomenclador.objects.filter(nomencladorpresupuesto=nomencladorpresupuesto, tiporecurso=2, descripcion=cols[2].strip().upper(), unidadmedida=None).exists():
                                    detallerecurso = DetalleNomenclador(nomencladorpresupuesto=nomencladorpresupuesto,
                                                                        tiporecurso=2,
                                                                        descripcion=cols[2].strip().upper(),
                                                                        unidadmedida=None,
                                                                        cantidadreferencia=cols[4],
                                                                        preciomaterialunitario=0,
                                                                        tarifareferencia=cols[5],
                                                                        jornadareferencia=0,
                                                                        costohorareferencia=costohorareferencia,
                                                                        rendimientoreferencia=cols[3],
                                                                        costoreferencia=costoreferencia,
                                                                        otroindirecto=cols[7])
                                    detallerecurso.save(request)
                                else:
                                    detallerecurso = DetalleNomenclador.objects.filter(nomencladorpresupuesto=nomencladorpresupuesto, tiporecurso=2, descripcion=cols[2].strip().upper(), unidadmedida=None)[0]
                                    detallerecurso.unidadmedida = None
                                    detallerecurso.cantidadreferencia = cols[4]
                                    detallerecurso.preciomaterialunitario = 0
                                    detallerecurso.tarifareferencia = cols[5]
                                    detallerecurso.jornadareferencia = 0
                                    detallerecurso.costohorareferencia = costohorareferencia
                                    detallerecurso.rendimientoreferencia = cols[3]
                                    detallerecurso.costoreferencia = costoreferencia
                                    detallerecurso.otroindirecto = cols[7]
                                    detallerecurso.save(request)
                                nomencladorpresupuesto.actualizar_recurso()
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
                form = ImportarArchivoRecursosSalariosXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION ANEXOS MANOS DE OBRAS',
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
                            if int(cols[0]) == 1:
                                # RECURSOS EQUIPOS INSERTAR
                                unidadmedida = None
                                if not UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper()).exists():
                                    unidadmedida = UnidadMedidaPresupuesto(descripcion=cols[1].strip())
                                    unidadmedida.save(request)
                                else:
                                    unidadmedida = UnidadMedidaPresupuesto.objects.filter(descripcion=cols[1].strip().upper())[0]
                                nomencladorpresupuesto = None
                                if not NomencladorPresupuesto.objects.filter(unidadmedida=unidadmedida, descripcion=cols[2].strip().upper()).exists():
                                    nomencladorpresupuesto = NomencladorPresupuesto(unidadmedida=unidadmedida, descripcion=cols[2].strip().upper())
                                    nomencladorpresupuesto.save(request)
                                else:
                                    nomencladorpresupuesto = NomencladorPresupuesto.objects.filter(unidadmedida=unidadmedida, descripcion=cols[2].strip().upper())[0]
                            if int(cols[0]) == 2:
                                # ANEXO DEL RECURSO MANO DE OBRA INSERTAR
                                costohorareferencia = Decimal(cols[4] * cols[5]).quantize(Decimal('.0001'))
                                rendimiento = Decimal(cols[3]).quantize(Decimal('.0001'))
                                costoreferencia = Decimal(costohorareferencia * rendimiento).quantize(Decimal('.0001'))
                                if not DetalleNomenclador.objects.filter(nomencladorpresupuesto=nomencladorpresupuesto, tiporecurso=3, descripcion=cols[2].strip().upper(), unidadmedida=None).exists():
                                    detallerecurso = DetalleNomenclador(nomencladorpresupuesto=nomencladorpresupuesto,
                                                                        tiporecurso=3,
                                                                        descripcion=cols[2].strip().upper(),
                                                                        unidadmedida=None,
                                                                        cantidadreferencia=cols[4],
                                                                        preciomaterialunitario=0,
                                                                        tarifareferencia=0,
                                                                        jornadareferencia=cols[5],
                                                                        costohorareferencia=costohorareferencia,
                                                                        rendimientoreferencia=cols[3],
                                                                        costoreferencia=costoreferencia,
                                                                        otroindirecto=cols[7])
                                    detallerecurso.save(request)
                                else:
                                    detallerecurso = DetalleNomenclador.objects.filter(nomencladorpresupuesto=nomencladorpresupuesto, tiporecurso=3, descripcion=cols[2].strip().upper(), unidadmedida=None)[0]
                                    detallerecurso.unidadmedida = None
                                    detallerecurso.cantidadreferencia = cols[4]
                                    detallerecurso.preciomaterialunitario = 0
                                    detallerecurso.tarifareferencia = 0
                                    detallerecurso.jornadareferencia = cols[5]
                                    detallerecurso.costohorareferencia = costohorareferencia
                                    detallerecurso.rendimientoreferencia = cols[3]
                                    detallerecurso.costoreferencia = costoreferencia
                                    detallerecurso.otroindirecto = cols[7]
                                    detallerecurso.save(request)
                                nomencladorpresupuesto.actualizar_recurso()
                        linea += 1
                    log(u'Importo anexos manos de obras obras', request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Recursos de Actividades'
                    data['form'] = NomencladorPresupuestoForm()
                    return render(request, 'ob_recursosactividad/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Recursos de Actividades'
                    data['recurso'] = recurso = NomencladorPresupuesto.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(recurso)
                    data['form'] = NomencladorPresupuestoForm(initial=initial)
                    return render(request, 'ob_recursosactividad/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Recursos de Actividades'
                    data['recurso'] = NomencladorPresupuesto.objects.get(pk=request.GET['id'])
                    return render(request, 'ob_recursosactividad/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'detrecursos':
                try:
                    data['title'] = u'Detalle de Recursos'
                    data['recurso'] = recurso = NomencladorPresupuesto.objects.get(pk=request.GET['id'])
                    data['detallerecursos'] = recurso.detallenomenclador_set.all().order_by('tiporecurso')
                    return render(request, 'ob_recursosactividad/detrecursos.html', data)
                except Exception as ex:
                    pass

            if action == 'adddetallerecurso':
                try:
                    data['title'] = u'Agregar Detalle de Recursos'
                    data['recurso'] = recurso = NomencladorPresupuesto.objects.get(pk=request.GET['id'])
                    form = DetalleNomencladorForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, 'ob_recursosactividad/adddetallerecurso.html', data)
                except Exception as ex:
                    pass

            if action == 'editdetallerecurso':
                try:
                    data['title'] = u'Modificar Detalle de Recursos'
                    data['detallerecurso'] = detallerecurso = DetalleNomenclador.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(detallerecurso)
                    form = DetalleNomencladorForm(initial=initial)
                    form.adicionar()
                    data['form'] = form
                    return render(request, 'ob_recursosactividad/editdetallerecurso.html', data)
                except Exception as ex:
                    pass

            if action == 'deletedetallerecurso':
                try:
                    data['title'] = u'Eliminar Detalle de Recursos'
                    data['detallerecurso'] = DetalleNomenclador.objects.get(pk=request.GET['id'])
                    return render(request, 'ob_recursosactividad/deletedetallerecurso.html', data)
                except Exception as ex:
                    pass

            if action == 'importarmateriales':
                try:
                    data['title'] = u'Importar Recursos Materiales'
                    data['form'] = ImportarArchivoRecursosMaterialesXLSForm()
                    return render(request, "ob_recursosactividad/importarmateriales.html", data)
                except Exception as ex:
                    pass

            if action == 'importarsalarios':
                try:
                    data['title'] = u'Importar Recursos Mano de Obra'
                    data['form'] = ImportarArchivoRecursosSalariosXLSForm()
                    return render(request, "ob_recursosactividad/importarsalarios.html", data)
                except Exception as ex:
                    pass

            if action == 'importarmaquinaria':
                try:
                    data['title'] = u'Importar Recursos Equipo'
                    data['form'] = ImportarArchivoRecursosMaquinariasXLSForm()
                    return render(request, "ob_recursosactividad/importarmaquinaria.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Recursos de Proyectos'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                recursos = NomencladorPresupuesto.objects.filter(descripcion__icontains=search, status=True)
            elif 'id' in request.GET:
                ids = request.GET['id']
                recursos = NomencladorPresupuesto.objects.filter(id=ids)
            else:
                recursos = NomencladorPresupuesto.objects.filter(status=True)
            paging = MiPaginador(recursos, 25)
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
            data['recursos'] = page.object_list
            return render(request, "ob_recursosactividad/view.html", data)