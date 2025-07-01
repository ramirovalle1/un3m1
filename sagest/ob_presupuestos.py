# -*- coding: UTF-8 -*-

from datetime import datetime
from decimal import Decimal
from googletrans import Translator
import xlrd
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.forms import PresupuestoObraForm, NomencladorPresupuestoForm, AprobacionPresupuestoObraForm, \
    ImportarArchivoPresupuestoObraForm, RechazarPresupuestoObraForm
from sagest.models import PresupuestoObra, ActividadPresupuestoObra, \
    AprobacionPresupuestoObra, CronogramaRecursoActividadPresupuestObra, CronogramaPresupuestoObra, GrupoActividadPresupuestObra, RecursoActividadPresupuestObra, NomencladorPresupuesto, \
    DetalleRecursoActividadPresupuestoObra, DetalleNomenclador, TIPO_ACTIVIDAD_PRESUPUESTO, UnidadMedidaPresupuesto, \
    ArchivoPresupuestoObra, null_to_decimal
from settings import ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata
from sga.forms import ImportarArchivoObrasXLSForm
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import Archivo, Persona


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
                f = PresupuestoObraForm(request.POST)
                if f.is_valid():
                    presupuesto = PresupuestoObra(nombre=f.cleaned_data['nombre'],
                                                  descripcion=f.cleaned_data['descripcion'],
                                                  fecha=datetime.now().date(),
                                                  porcentajeindirectoutilidad=f.cleaned_data['porcentajeindirectoutilidad'],
                                                  duracion=f.cleaned_data['duracion'],
                                                  ubicacion=f.cleaned_data['ubicacion'],
                                                  elaborado=request.session['persona'])
                    presupuesto.save(request)
                    presupuesto.generar_cronograma_presupuesto()
                    log(u'Adiciono un nuevo proyecto: %s' % presupuesto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'aprobar':
            try:
                presupuesto = PresupuestoObra.objects.get(pk=request.POST['id'])

                f = AprobacionPresupuestoObraForm(request.POST)
                if f.is_valid():
                    if presupuesto.valor_meses() < presupuesto.valor:
                        return JsonResponse({"result": "bad", "mensaje": u'El valor del Presupuesto no se Programo correctamente'})
                    contratista = Persona.objects.get(pk=f.cleaned_data['contratista'])
                    fiscalizador = Persona.objects.get(pk=f.cleaned_data['fiscalizador'])
                    administradorcontrato = Persona.objects.get(pk=f.cleaned_data['administradorcontrato'])
                    aprobar = AprobacionPresupuestoObra(presupuestoobra=presupuesto,
                                                        contratonumero=f.cleaned_data['contratonumero'],
                                                        fechainicio=f.cleaned_data['fechainicio'],
                                                        fechafin=f.cleaned_data['fechafin'],
                                                        contratista=contratista.nombre_completo(),
                                                        fiscalizador=fiscalizador.nombre_completo(),
                                                        administradorcontrato=administradorcontrato.nombre_completo())
                    aprobar.save(request)
                    presupuesto.estado = 2
                    presupuesto.save(request)
                    log(u'Aprobacion del nuevo proyecto: %s' % aprobar, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'rechazar':
            try:
                presupuesto = PresupuestoObra.objects.get(pk=request.POST['id'])
                f = RechazarPresupuestoObraForm(request.POST)
                if f.is_valid():
                    presupuesto.observacion = f.cleaned_data['observacion']
                    presupuesto.estado = 3
                    presupuesto.save(request)
                log(u'Rechazar Presupuesto: %s' % presupuesto, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'addactividad':
            try:
                presupuesto = PresupuestoObra.objects.get(pk=request.POST['idp'])
                actividad = ActividadPresupuestoObra(presupuestoobra=presupuesto,
                                                     descripcion=request.POST['valor'])
                actividad.save(request)
                log(u'Adiciono una nueva actividad de presupuesto: %s' % actividad, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'editactividad':
            try:
                actividad = ActividadPresupuestoObra.objects.get(pk=request.POST['id'])
                actividad.descripcion = request.POST['valor']
                actividad.save(request)
                log(u'Modifico una nueva actividad de presupuesto: %s' % actividad, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'edit':
            try:
                presupuesto = PresupuestoObra.objects.get(pk=request.POST['id'])
                grupo = GrupoActividadPresupuestObra.objects.filter(actividadpresupuestoobra__presupuestoobra=presupuesto)[0]
                f = PresupuestoObraForm(request.POST)
                if f.is_valid():
                    presupuesto.nombre = f.cleaned_data['nombre']
                    presupuesto.descripcion = f.cleaned_data['descripcion']
                    presupuesto.duracion = f.cleaned_data['duracion']
                    presupuesto.porcentajeindirectoutilidad = f.cleaned_data['porcentajeindirectoutilidad']
                    presupuesto.ubicacion = f.cleaned_data['ubicacion']
                    presupuesto.elaborado = request.session['persona']
                    presupuesto.save(request)
                    presupuesto.generar_cronograma_presupuesto()
                    if f.cleaned_data['porcentajeindirectoutilidad']:
                        for recurso in RecursoActividadPresupuestObra.objects.filter(grupoactividadpresupuestobra=grupo):
                            recurso.actualizar_recursoactividad()
                        grupo.actualizar_grupo_presupuesto()
                        actividad = grupo.actividadpresupuestoobra
                        actividad.actualizar_actividad()
                        presupuesto.actualizar_presupuesto()
                    return JsonResponse({"result": "ok"})

                else:
                     raise NameError('Errod al guardar los datos')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje": translator.translate(ex.__str__(),'es').text})

        if action == 'delete':
            try:
                presupuesto = PresupuestoObra.objects.get(pk=request.POST['id'])
                presupuesto.status = False
                presupuesto.save(request)
                log(u'Elimino presupuesto obra: %s [%s]' % (presupuesto,presupuesto.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'addgrupo':
            try:
                data['actividad'] = actividad = ActividadPresupuestoObra.objects.get(pk=request.POST['ida'])
                grupo = GrupoActividadPresupuestObra(actividadpresupuestoobra=actividad,
                                                     descripcion=request.POST['valor'])
                grupo.save(request)
                actividad.actualizar_actividad()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                data['presupuesto'] = presupuesto
                data['grupos'] = actividad.grupoactividadpresupuestobra_set.all()
                template = get_template("ob_presupuestos/detalleactividad.html")
                json_content = template.render(data)
                log(u'Adiciono un nuevo proyecto: %s' % grupo, request, "add")
                return JsonResponse({"result": "ok", 'plantilla': json_content, 'presupuestototal': str(presupuesto.valor), 'actividadid': actividad.id, 'actividadvalor': str(actividad.valor)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'deleteactividad':
            try:
                actividad = ActividadPresupuestoObra.objects.get(pk=request.POST['id'])
                for grupo in actividad.grupoactividadpresupuestobra_set.all():
                    for recurso in grupo.recursoactividadpresupuestobra_set.all():
                        recurso.detallerecursoactividadpresupuestoobra_set.all().delete()
                        recurso.delete()
                    grupo.delete()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                log(u'Elimino actividad de presupuesto: %s' % actividad, request, "del")
                actividad.delete()
                return JsonResponse({"result": "ok", 'presupuestototal': str(presupuesto.valor)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'delarchivo':
            try:
                archivo = ArchivoPresupuestoObra.objects.get(pk=request.POST['id'])
                log(u'Elimino archivo de presupuesto: %s' % archivo, request, "del")
                archivo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'grupos':
            try:
                data['actividad'] = actividad = ActividadPresupuestoObra.objects.get(pk=int(request.POST['id']))
                data['grupos'] = actividad.grupoactividadpresupuestobra_set.all()
                data['presupuesto'] = actividad.presupuestoobra
                template = get_template("ob_presupuestos/detalleactividad.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'plantilla': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'editgrupo':
            try:
                grupo = GrupoActividadPresupuestObra.objects.get(pk=request.POST['idg'])
                grupo.descripcion = request.POST['valor']
                grupo.save(request)
                log(u'Modifico una nueva actividad de presupuesto: %s' % grupo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'delgrupo':
            try:
                grupo = GrupoActividadPresupuestObra.objects.get(pk=request.POST['id'])
                actividad = grupo.actividadpresupuestoobra
                for recurso in grupo.recursoactividadpresupuestobra_set.all():
                    recurso.detallerecursoactividadpresupuestoobra_set.all().delete()
                    recurso.delete()
                log(u'Elimino grupo de presupuesto: %s' % grupo, request, "del")
                grupo.delete()
                actividad.actualizar_actividad()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                return JsonResponse({"result": "ok", 'presupuestototal': str(presupuesto.valor), 'actividadid': actividad.id, 'actividadvalor': str(actividad.valor)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'addrecurso':
            try:
                data['grupo'] = grupo = GrupoActividadPresupuestObra.objects.get(pk=int(request.POST['idg']))
                recurso_selecionado = NomencladorPresupuesto.objects.get(pk=int(request.POST['idr']))
                recurso = RecursoActividadPresupuestObra(grupoactividadpresupuestobra=grupo,
                                                         descripcion=recurso_selecionado.descripcion,
                                                         unidadmedida=recurso_selecionado.unidadmedida,
                                                         cantidad=1)
                recurso.save(request)
                recurso.generar_cronograma_recurso()
                detrecursos_nomenclador = DetalleNomenclador.objects.filter(nomencladorpresupuesto=recurso_selecionado.pk)
                for detrecurso_selecionado in detrecursos_nomenclador:
                    detrecurso = DetalleRecursoActividadPresupuestoObra(recursoactividadpresupuestobra=recurso,
                                                                        tiporecurso=detrecurso_selecionado.tiporecurso,
                                                                        descripcion=detrecurso_selecionado.descripcion,
                                                                        unidadmedida=detrecurso_selecionado.unidadmedida,
                                                                        cantidadreferencia=detrecurso_selecionado.cantidadreferencia,
                                                                        preciomaterialunitario=detrecurso_selecionado.preciomaterialunitario,
                                                                        tarifareferencia=detrecurso_selecionado.tarifareferencia,
                                                                        jornadareferencia=detrecurso_selecionado.jornadareferencia,
                                                                        costohorareferencia=detrecurso_selecionado.costohorareferencia,
                                                                        rendimientoreferencia=detrecurso_selecionado.rendimientoreferencia,
                                                                        otroindirecto=detrecurso_selecionado.otroindirecto,
                                                                        costoreferencia=detrecurso_selecionado.costoreferencia)
                    detrecurso.save(request)
                    log(u'Adiciono detalle recurso de actividad de presupuesto obra: %s' % detrecurso, request, "add")
                recurso.actualizar_recursoactividad()
                grupo.actualizar_grupo_presupuesto()
                actividad = grupo.actividadpresupuestoobra
                actividad.actualizar_actividad()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                data['recursos'] = grupo.recursoactividadpresupuestobra_set.all()
                data['presupuesto'] = presupuesto
                template = get_template("ob_presupuestos/items.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'plantilla': json_content, 'presupuestototal': str(presupuesto.valor), 'actividadid': actividad.id, 'actividadvalor': str(actividad.valor), 'grupoid': grupo.id, 'grupovalor': str(grupo.valor)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'delrecurso':
            try:
                recurso = RecursoActividadPresupuestObra.objects.get(pk=request.POST['id'])
                grupo = recurso.grupoactividadpresupuestobra
                recurso.detallerecursoactividadpresupuestoobra_set.all().delete()
                recurso.cronogramarecursoactividadpresupuestobra_set.all().delete()
                log(u'Elimino recurso de presupuesto: %s' % recurso, request, "del")
                recurso.delete()
                grupo.actualizar_grupo_presupuesto()
                actividad = grupo.actividadpresupuestoobra
                actividad.actualizar_actividad()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                return JsonResponse({"result": "ok", "valor": str(recurso.valor), "cantidad": str(recurso.cantidad), 'presupuestototal': str(presupuesto.valor), 'actividadid': actividad.id, 'actividadvalor': str(actividad.valor), 'grupoid': grupo.id, 'grupovalor': str(grupo.valor)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'editcantidarecurso':
            try:
                recurso = RecursoActividadPresupuestObra.objects.get(pk=request.POST['idr'])
                cantidad = Decimal(request.POST['cantidad'])
                recurso.cantidad = cantidad
                recurso.save(request)
                for cronograma in recurso.cronogramarecursoactividadpresupuestobra_set.all():
                    cronograma.valor = 0.00
                    cronograma.save(request)
                recurso.actualizar_recursoactividad()
                grupo = recurso.grupoactividadpresupuestobra
                grupo.actualizar_grupo_presupuesto()
                actividad = grupo.actividadpresupuestoobra
                actividad.actualizar_actividad()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                log(u'Modifico una nueva actividad de presupuesto: %s' % recurso, request, "edit")
                return JsonResponse({"result": "ok", "valor": str(recurso.valor), "cantidad": str(recurso.cantidad), 'presupuestototal': str(presupuesto.valor), 'actividadid': actividad.id, 'actividadvalor': str(actividad.valor), 'grupoid': grupo.id, 'grupovalor': str(grupo.valor)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al editar los datos'})

        if action == 'items':
            try:
                data['grupo'] = grupo = GrupoActividadPresupuestObra.objects.get(pk=int(request.POST['id']))
                data['recursos'] = grupo.recursoactividadpresupuestobra_set.all().order_by('id')
                data['presupuesto'] = grupo.actividadpresupuestoobra.presupuestoobra
                template = get_template("ob_presupuestos/items.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'plantilla': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u'Error al obtener los datos'})

        if action == 'itemsdetrecurso':
            try:
                data['recurso'] = recurso = RecursoActividadPresupuestObra.objects.get(pk=request.POST['idr'])
                data['detalleequipos'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=2)
                data['detallemanoobra'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=3)
                data['detallemateriales'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=4)
                data['detalletransporte'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=5)
                data['presupuesto'] = recurso.grupoactividadpresupuestobra.actividadpresupuestoobra.presupuestoobra
                opciones = TIPO_ACTIVIDAD_PRESUPUESTO
                unidad_medida = list(UnidadMedidaPresupuesto.objects.values_list('id', 'descripcion'))
                template = get_template("ob_presupuestos/itemsdetrecurso.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'plantilla': json_content, 'opciones': opciones, 'unidad_medida': unidad_medida})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u'Error al obtener los datos'})

        if action == 'editdetrecurso':
            try:
                unidadmedida = UnidadMedidaPresupuesto.objects.get(pk=int(request.POST['unid']))
                cantidad = Decimal(request.POST['cant']).quantize(Decimal('.01'))
                tarifa = Decimal(request.POST['tarif']).quantize(Decimal('.0001'))
                jornal = Decimal(request.POST['jorn']).quantize(Decimal('.0001'))
                preciou = Decimal(request.POST['prec']).quantize(Decimal('.0001'))
                otroindi = Decimal(request.POST['otroindi']).quantize(Decimal('.0001'))
                rendimiento = Decimal(request.POST['rend']).quantize(Decimal('.0001'))
                costohorareferencia = 0
                costoreferencia = 0
                if request.POST['tip'] == '2':
                    costohorareferencia = Decimal(cantidad * tarifa).quantize(Decimal('.0001'))
                    costoreferencia = Decimal(costohorareferencia * rendimiento).quantize(Decimal('.0001'))
                if request.POST['tip'] == '3':
                    costohorareferencia = Decimal(cantidad * jornal).quantize(Decimal('.0001'))
                    costoreferencia = Decimal(costohorareferencia * rendimiento).quantize(Decimal('.0001'))
                if request.POST['tip'] == '4':
                    costoreferencia = Decimal(cantidad * preciou).quantize(Decimal('.0001'))
                if request.POST['tip'] == '5':
                    costoreferencia = Decimal(cantidad * tarifa).quantize(Decimal('.0001'))
                detallerecurso = DetalleRecursoActividadPresupuestoObra.objects.get(pk=int(request.POST['iddr']))
                detallerecurso.tiporecurso = request.POST['tip']
                detallerecurso.descripcion = request.POST['des']
                detallerecurso.unidadmedida = unidadmedida
                detallerecurso.cantidadreferencia = cantidad
                detallerecurso.preciomaterialunitario = preciou
                detallerecurso.tarifareferencia = tarifa
                detallerecurso.jornadareferencia = jornal
                detallerecurso.costohorareferencia = costohorareferencia
                detallerecurso.rendimientoreferencia = rendimiento
                detallerecurso.otroindirecto = otroindi
                detallerecurso.costoreferencia = costoreferencia
                detallerecurso.save(request)
                recurso = detallerecurso.recursoactividadpresupuestobra
                for cronograma in recurso.cronogramarecursoactividadpresupuestobra_set.all():
                    cronograma.valor = 0.00
                    cronograma.save(request)
                recurso.actualizar_recursoactividad()
                grupo = recurso.grupoactividadpresupuestobra
                grupo.actualizar_grupo_presupuesto()
                actividad = grupo.actividadpresupuestoobra
                actividad.actualizar_actividad()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                data['detalleequipos'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=2)
                data['detallemanoobra'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=3)
                data['detallemateriales'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=4)
                data['detalletransporte'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=5)
                data['presupuesto'] = presupuesto
                template = get_template("ob_presupuestos/itemsdetrecurso.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'plantilla': json_content, 'presupuestototal': str(presupuesto.valor), 'actividadid': actividad.id, 'actividadvalor': str(actividad.valor), 'grupoid': grupo.id, 'grupovalor': str(grupo.valor), 'recursoid': recurso.id, 'recursodescripcion': recurso.descripcion, 'recursounidadmedida': str(recurso.unidadmedida), 'recursocostoequipos': str(recurso.costoequipos), 'recursocostosmanoobra': str(recurso.costosmanoobra), 'recursocostomateriales': str(recurso.costomateriales), 'recursocostotransporte': str(recurso.costotransporte), 'recursoindirectoutilidad': str(recurso.indirectoutilidad), 'recursocostootros': str(recurso.costootros), 'recursocostototal': str(recurso.costototal), 'recursocantidad': str(recurso.cantidad), 'recursovalor': str(recurso.valor), 'recursopreciounitario': str(recurso.preciounitario)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al editar los datos'})

        if action == 'delitemdetrecurso':
            try:
                detallerecurso = DetalleRecursoActividadPresupuestoObra.objects.get(pk=request.POST['id'])
                log(u'Elimino actividad de presupuesto: %s' % detallerecurso, request, "del")
                detallerecurso.delete()
                recurso = detallerecurso.recursoactividadpresupuestobra
                for cronograma in recurso.cronogramarecursoactividadpresupuestobra_set.all():
                    cronograma.valor = 0.00
                    cronograma.save(request)
                recurso.actualizar_recursoactividad()
                grupo = recurso.grupoactividadpresupuestobra
                grupo.actualizar_grupo_presupuesto()
                actividad = grupo.actividadpresupuestoobra
                actividad.actualizar_actividad()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                return JsonResponse({"result": "ok", 'presupuestototal': str(presupuesto.valor), 'actividadid': actividad.id, 'actividadvalor': str(actividad.valor), 'grupoid': grupo.id, 'grupovalor': str(grupo.valor), 'recursoid': recurso.id, 'recursodescripcion': recurso.descripcion, 'recursounidadmedida': str(recurso.unidadmedida), 'recursocostoequipos': str(recurso.costoequipos), 'recursocostosmanoobra': str(recurso.costosmanoobra), 'recursocostomateriales': str(recurso.costomateriales), 'recursocostotransporte': str(recurso.costotransporte), 'recursocostootros': str(recurso.costootros), 'recursocostototal': str(recurso.costototal), 'recursocantidad': str(recurso.cantidad), 'recursovalor': str(recurso.valor)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'adddetrecurso':
            try:
                cantidad = Decimal(request.POST['cant']).quantize(Decimal('.01'))
                tarifa = Decimal(request.POST['tarif']).quantize(Decimal('.0001'))
                jornal = Decimal(request.POST['jorn']).quantize(Decimal('.0001'))
                preciou = Decimal(request.POST['prec']).quantize(Decimal('.0001'))
                otroindi = Decimal(request.POST['otroindi']).quantize(Decimal('.0001'))
                rendimiento = Decimal(request.POST['rend']).quantize(Decimal('.0001'))
                costohorareferencia = 0
                costoreferencia = 0
                if request.POST['tip'] == '2':
                    costohorareferencia = Decimal(cantidad * tarifa).quantize(Decimal('.0001'))
                    costoreferencia = Decimal(costohorareferencia * rendimiento).quantize(Decimal('.0001'))
                if request.POST['tip'] == '3':
                    costohorareferencia = Decimal(cantidad * jornal).quantize(Decimal('.0001'))
                    costoreferencia = Decimal(costohorareferencia * rendimiento).quantize(Decimal('.0001'))
                if request.POST['tip'] == '4':
                    costoreferencia = Decimal(cantidad * preciou).quantize(Decimal('.0001'))
                if request.POST['tip'] == '5':
                    costoreferencia = Decimal(cantidad * tarifa).quantize(Decimal('.0001'))

                recurso = RecursoActividadPresupuestObra.objects.get(pk=int(request.POST['idr']))
                unidadmedida = UnidadMedidaPresupuesto.objects.get(pk=int(request.POST['unid']))

                detrecurso = DetalleRecursoActividadPresupuestoObra(recursoactividadpresupuestobra=recurso,
                                                                    tiporecurso=int(request.POST['tip']),
                                                                    descripcion=request.POST['des'],
                                                                    unidadmedida=unidadmedida,
                                                                    cantidadreferencia=cantidad,
                                                                    preciomaterialunitario=preciou,
                                                                    tarifareferencia=tarifa,
                                                                    jornadareferencia=jornal,
                                                                    costohorareferencia=costohorareferencia,
                                                                    rendimientoreferencia=rendimiento,
                                                                    otroindirecto=otroindi,
                                                                    costoreferencia=costoreferencia,)
                detrecurso.save(request)
                for cronograma in recurso.cronogramarecursoactividadpresupuestobra_set.all():
                    cronograma.valor = 0.00
                    cronograma.save(request)
                recurso.actualizar_recursoactividad()
                grupo = recurso.grupoactividadpresupuestobra
                grupo.actualizar_grupo_presupuesto()
                actividad = grupo.actividadpresupuestoobra
                actividad.actualizar_actividad()
                presupuesto = actividad.presupuestoobra
                presupuesto.actualizar_presupuesto()
                data['detalleequipos'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=2)
                data['detallemanoobra'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=3)
                data['detallemateriales'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=4)
                data['detalletransporte'] = recurso.detallerecursoactividadpresupuestoobra_set.filter(tiporecurso=5)
                data['presupuesto'] = presupuesto
                template = get_template("ob_presupuestos/itemsdetrecurso.html")
                json_content = template.render(data)
                return JsonResponse(
                    {"result": "ok", 'plantilla': json_content, 'presupuestototal': str(presupuesto.valor),
                     'actividadid': actividad.id, 'actividadvalor': str(actividad.valor), 'grupoid': grupo.id,
                     'grupovalor': str(grupo.valor), 'recursoid': recurso.id,
                     'recursodescripcion': recurso.descripcion, 'recursounidadmedida': str(recurso.unidadmedida),
                     'recursocostoequipos': str(recurso.costoequipos),
                     'recursocostosmanoobra': str(recurso.costosmanoobra),
                     'recursocostomateriales': str(recurso.costomateriales),
                     'recursocostotransporte': str(recurso.costotransporte),
                     'recursocostootros': str(recurso.costootros), 'recursocostototal': str(recurso.costototal),
                     'recursocantidad': str(recurso.cantidad), 'recursovalor': str(recurso.valor), 'recursopreciounitario': str(recurso.preciounitario)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'subir':
            try:
                presupuesto = PresupuestoObra.objects.get(pk=request.POST['id'])
                f = ImportarArchivoPresupuestoObraForm(request.POST, request.FILES)
                if f.is_valid():
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("presupuesto_", nfile._name)
                    archivopresupuesto = ArchivoPresupuestoObra(presupuestoobra=presupuesto,
                                                                tipoarchivo=f.cleaned_data['tipoarchivo'],
                                                                nombre=f.cleaned_data['nombre'],
                                                                archivo=nfile, )
                    archivopresupuesto.save(request)
                    log(u'Add archivo de Presupuesto: %s' % archivopresupuesto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"El archivo no tiene el formato correcto."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'importar':
            try:
                form = ImportarArchivoObrasXLSForm(request.POST, request.FILES)
                presupuestoobra = PresupuestoObra.objects.filter(pk=request.POST['id'])[0]
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION PRESPUESTO OBRAS',
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
                                # ACTIVIDADES INSERTAR
                                actividad = None
                                if not ActividadPresupuestoObra.objects.filter(presupuestoobra=presupuestoobra, descripcion=cols[1].strip().upper()).exists():
                                    actividad = ActividadPresupuestoObra(presupuestoobra=presupuestoobra,
                                                                         descripcion=cols[1].strip().upper())
                                    actividad.save(request)
                                else:
                                    actividad = ActividadPresupuestoObra.objects.filter(presupuestoobra=presupuestoobra, descripcion=cols[1].strip().upper())[0]
                            if int(cols[0]) == 2:
                                # GRUPO DE LA ACTIVIDAD INSERTAR
                                grupo = None
                                if not GrupoActividadPresupuestObra.objects.filter(actividadpresupuestoobra=actividad, descripcion=cols[1].strip().upper()).exists():
                                    grupo = GrupoActividadPresupuestObra(actividadpresupuestoobra=actividad,
                                                                         descripcion=cols[1].strip().upper())
                                    grupo.save(request)
                                else:
                                    grupo = GrupoActividadPresupuestObra.objects.filter(actividadpresupuestoobra=actividad, descripcion=cols[1].strip().upper())[0]
                                actividad.actualizar_actividad()
                                presupuesto = actividad.presupuestoobra
                                presupuesto.actualizar_presupuesto()
                            if int(cols[0]) == 3:
                                if NomencladorPresupuesto.objects.filter(descripcion=cols[1].strip().upper()).exists():
                                    recurso_selecionado = NomencladorPresupuesto.objects.filter(descripcion=cols[1].strip().upper())[0]
                                    recurso = RecursoActividadPresupuestObra(grupoactividadpresupuestobra=grupo,
                                                                             descripcion=recurso_selecionado.descripcion,
                                                                             unidadmedida=recurso_selecionado.unidadmedida,
                                                                             cantidad=int(cols[2]))
                                    recurso.save(request)
                                    recurso.generar_cronograma_recurso()
                                    detrecursos_nomenclador = DetalleNomenclador.objects.filter(nomencladorpresupuesto=recurso_selecionado.pk)
                                    for detrecurso_selecionado in detrecursos_nomenclador:
                                        detrecurso = DetalleRecursoActividadPresupuestoObra(recursoactividadpresupuestobra=recurso,
                                                                                            tiporecurso=detrecurso_selecionado.tiporecurso,
                                                                                            descripcion=detrecurso_selecionado.descripcion,
                                                                                            unidadmedida=detrecurso_selecionado.unidadmedida,
                                                                                            cantidadreferencia=detrecurso_selecionado.cantidadreferencia,
                                                                                            preciomaterialunitario=detrecurso_selecionado.preciomaterialunitario,
                                                                                            tarifareferencia=detrecurso_selecionado.tarifareferencia,
                                                                                            jornadareferencia=detrecurso_selecionado.jornadareferencia,
                                                                                            costohorareferencia=detrecurso_selecionado.costohorareferencia,
                                                                                            rendimientoreferencia=detrecurso_selecionado.rendimientoreferencia,
                                                                                            otroindirecto=detrecurso_selecionado.otroindirecto,
                                                                                            costoreferencia=detrecurso_selecionado.costoreferencia, )
                                        detrecurso.save(request)
                                    recurso.actualizar_recursoactividad()
                                    grupo.actualizar_grupo_presupuesto()
                                    actividad = grupo.actividadpresupuestoobra
                                    actividad.actualizar_actividad()
                                    presupuesto = actividad.presupuestoobra
                                    presupuesto.actualizar_presupuesto()
                                else:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"Error no existe este recurso %s " % cols[1].strip().upper()})
                        linea += 1
                    log(u'Importo prespuesto obras: %s' % presupuestoobra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cronorecurso':
            try:
                data['recurso'] = recurso = RecursoActividadPresupuestObra.objects.get(pk=int(request.POST['id']))
                data['cronorecursos'] = recurso.cronogramarecursoactividadpresupuestobra_set.all()
                data['presupuesto'] = recurso.grupoactividadpresupuestobra.actividadpresupuestoobra.presupuestoobra
                template = get_template("ob_presupuestos/planificacionmes.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'plantilla': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al obtener los datos'})

        if action == 'addcronorecurso':
            try:
                mes = int(request.POST['mes'])
                valor = Decimal(request.POST['valor'])
                recurso = RecursoActividadPresupuestObra.objects.get(pk=request.POST['idr'])
                total_recursos = null_to_decimal(CronogramaRecursoActividadPresupuestObra.objects.filter(recursoactividadpresupuestobra=recurso).aggregate(valor=Sum('valor'))['valor'])
                total_recursos += valor
                if total_recursos <= recurso.valor:
                    if not CronogramaRecursoActividadPresupuestObra.objects.filter(recursoactividadpresupuestobra=recurso, mes=mes).exists():
                        cronorecurso = CronogramaRecursoActividadPresupuestObra(recursoactividadpresupuestobra=recurso,
                                                                                mes=mes,
                                                                                valor=valor)
                        cronorecurso.save(request)
                    else:
                        cronorecurso = CronogramaRecursoActividadPresupuestObra.objects.filter(recursoactividadpresupuestobra=recurso, mes=mes)[0]
                        cronorecurso.valor = valor
                        cronorecurso.save(request)
                    presupuesto = recurso.grupoactividadpresupuestobra.actividadpresupuestoobra.presupuestoobra
                    valor_mes = null_to_decimal(CronogramaRecursoActividadPresupuestObra.objects.filter(recursoactividadpresupuestobra__grupoactividadpresupuestobra__actividadpresupuestoobra__presupuestoobra=presupuesto, mes=mes).aggregate(valor=Sum('valor'))['valor'])
                    if not presupuesto.cronogramapresupuestoobra_set.filter(mes=mes).exists():
                        cronopresupuesto = CronogramaPresupuestoObra(presupuestoobra=presupuesto,
                                                                     mes=mes,
                                                                     planificado=valor_mes)
                        cronopresupuesto.save(request)
                    else:
                        cronopresupuesto = presupuesto.cronogramapresupuestoobra_set.filter(mes=mes)[0]
                        cronopresupuesto.planificado = valor_mes
                        cronopresupuesto.save(request)
                    presupuesto.actualiza_planificado()
                    log(u'Modifico Cronograma Pres y Recurs : %s' % recurso, request, "edit")
                    return JsonResponse({"result": "ok", 'total_recursos': str(total_recursos)})
                return JsonResponse({"result": "ok", 'superavalor': 1, 'valorrecomendado': str(total_recursos - recurso.valor)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar presupuesto'
                    data['form'] = PresupuestoObraForm()
                    return render(request, 'ob_presupuestos/add.html', data)
                except Exception as ex:
                    pass

            if action == 'aprobar':
                try:
                    data['title'] = u'Aprobar presupuesto'
                    data['presupuesto'] = PresupuestoObra.objects.get(pk=request.GET['id'])
                    data['form'] = AprobacionPresupuestoObraForm()
                    return render(request, 'ob_presupuestos/aprobar.html', data)
                except Exception as ex:
                    pass

            if action == 'rechazar':
                try:
                    data['title'] = u'Rechazar presupuesto'
                    data['presupuesto'] = PresupuestoObra.objects.get(pk=request.GET['id'])
                    data['form'] = RechazarPresupuestoObraForm()
                    return render(request, 'ob_presupuestos/rechazar.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar presupuesto'
                    data['presupuesto'] = presupuesto = PresupuestoObra.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(presupuesto)
                    data['form'] = PresupuestoObraForm(initial=initial)
                    return render(request, 'ob_presupuestos/edit.html', data)

                except Exception as ex:
                    pass

            if action == 'documentos':
                try:
                    data['title'] = u'Documentos Presupuesto de Obra'
                    data['presupuesto'] = presupuesto = PresupuestoObra.objects.get(pk=request.GET['id'])
                    data['archivos'] = presupuesto.archivopresupuestoobra_set.all()
                    return render(request, "ob_presupuestos/documentos.html", data)
                except Exception as ex:
                    pass

            if action == 'estadistica':
                try:
                    data['title'] = u'Estadistica Presupuesto de Obra'
                    data['presupuesto'] = presupuesto = PresupuestoObra.objects.get(pk=request.GET['id'])
                    data['cronogramapresupuesto'] = CronogramaPresupuestoObra.objects.filter(presupuestoobra=presupuesto)
                    return render(request, "ob_presupuestos/estadistica.html", data)
                except Exception as ex:
                    pass

            if action == 'subir':
                try:
                    data['title'] = u'Subir Archivo'
                    data['presupuesto'] = presupuesto = PresupuestoObra.objects.get(pk=request.GET['id'])
                    form = ImportarArchivoPresupuestoObraForm()
                    data['form'] = form
                    return render(request, "ob_presupuestos/subir.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar presupuesto'
                    data['presupuesto'] = PresupuestoObra.objects.get(pk=request.GET['id'])
                    return render(request, 'ob_presupuestos/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'deleteactividad':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['actividad'] = actividad = ActividadPresupuestoObra.objects.get(pk=request.GET['id'])
                    return render(request, 'ob_presupuestos/deleteactividad.html', data)
                except Exception as ex:
                    pass

            if action == 'delarchivo':
                try:
                    data['title'] = u'Eliminar Archivo'
                    data['archivo'] = archivo = ArchivoPresupuestoObra.objects.get(pk=request.GET['id'])
                    data['presupuesto'] = archivo.presupuestoobra
                    return render(request, 'ob_presupuestos/delarchivo.html', data)
                except Exception as ex:
                    pass

            if action == 'actividades':
                try:
                    data['title'] = u'Actividades de obras'
                    data['presupuesto'] = presupuesto = PresupuestoObra.objects.get(pk=request.GET['id'])
                    data['actividades'] = presupuesto.actividadpresupuestoobra_set.all()
                    data['form'] = NomencladorPresupuestoForm()
                    return render(request, 'ob_presupuestos/actividades.html', data)
                except Exception as ex:
                    pass

            if action == 'reporte':
                try:
                    presupuesto = PresupuestoObra.objects.get(pk=request.GET['id'])
                    actividades = presupuesto.actividadpresupuestoobra_set.all()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=presupuesto.xls'
                    book = xlwt.Workbook()
                    style = xlwt.easyxf('font: bold on; border: left thin, right thin, top thin, bottom thin; align: wrap on, vert centre, horiz center;')
                    style1 = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center;')
                    style2 = xlwt.easyxf('font: bold on; align: wrap on, vert centre;')
                    style3 = xlwt.easyxf('align: wrap on, vert centre, horiz center;')
                    style4 = xlwt.easyxf('align: wrap on, vert centre;')
                    style5 = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center;')
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'dd/mm/yyyy'
                    sheet1 = book.add_sheet('PRESUPUESTO')
                    estilo = xlwt.easyxf(
                        'font: height 300, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    sheet1.write_merge(1, 1, 1, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    sheet1.col(0).width = 1000
                    sheet1.col(1).width = 2900
                    sheet1.col(2).width = 15000
                    sheet1.col(3).width = 2900
                    sheet1.col(4).width = 2900
                    sheet1.col(5).width = 4400
                    sheet1.col(6).width = 3800
                    sheet1.write_merge(4, 4, 1, 1, 'N.', style)
                    sheet1.write_merge(4, 4, 2, 2, 'DESCRIPCION', style)
                    sheet1.write_merge(4, 4, 3, 3, 'UNIDAD', style)
                    sheet1.write_merge(4, 4, 4, 4, 'CANTIDAD', style)
                    sheet1.write_merge(4, 4, 5, 5, 'PRECIO UNITARIO', style)
                    sheet1.write_merge(4, 4, 6, 6, 'PRECIO TOTAL', style)
                    a = 4
                    nivel1 = 6
                    item1 = 1
                    item2 = 0.01
                    for actividad in presupuesto.actividadpresupuestoobra_set.all():
                        sheet1.write_merge(nivel1, nivel1, 2, 5, actividad.descripcion, style1)
                        nivel1 += 1
                        for grupo in actividad.grupoactividadpresupuestobra_set.all():
                            sheet1.write_merge(nivel1, nivel1, 1, 1, item1, style3)
                            sheet1.write_merge(nivel1, nivel1, 2, 2, grupo.descripcion, style2)
                            item1 += 1
                            item2 += 1.00
                            nivel1 += 1
                            for recurso in grupo.recursoactividadpresupuestobra_set.all():
                                sheet1.write_merge(nivel1, nivel1, 1, 1, str(item2), style3)
                                sheet1.write_merge(nivel1, nivel1, 2, 2, recurso.descripcion, style4)
                                sheet1.write_merge(nivel1, nivel1, 3, 3, str(recurso.unidadmedida.descripcion), style3)
                                sheet1.write_merge(nivel1, nivel1, 4, 4, str(Decimal(recurso.cantidad).quantize(Decimal('.01'))), style3)
                                sheet1.write_merge(nivel1, nivel1, 5, 5, '$' + str(Decimal(recurso.preciounitario).quantize(Decimal('.01'))), style3)
                                sheet1.write_merge(nivel1, nivel1, 6, 6, '$' + str(recurso.valor), style3)
                                nivel1 += 1
                                item2 += 0.01
                            item2 = 1.01
                            nivel1 += 1
                        sheet1.write_merge(nivel1, nivel1, 4, 5, 'SUB TOTAL ' + actividad.descripcion, style2)
                        sheet1.write_merge(nivel1, nivel1, 6, 6, '$' + str(Decimal(actividad.valor).quantize(Decimal('.01'))), style5)
                        nivel1 += 1
                    book.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar datos del Presupuesto de Obras'
                    data['presupuestoobra'] = PresupuestoObra.objects.filter(pk=request.GET['id'])[0]
                    data['form'] = ImportarArchivoObrasXLSForm()
                    return render(request, "ob_presupuestos/importar.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Presupuestos de obras'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                presupuestos = PresupuestoObra.objects.filter(descripcion__icontains=search, status=True)
            elif 'id' in request.GET:
                ids = request.GET['id']
                presupuestos = PresupuestoObra.objects.filter(id=ids, status=True)
            else:
                presupuestos = PresupuestoObra.objects.filter(status=True)
            paging = MiPaginador(presupuestos, 25)
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
            data['presupuestos'] = page.object_list
            return render(request, "ob_presupuestos/view.html", data)