# -*- coding: latin-1 -*-
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from investigacion.models import InvCabAreas, AreaUnesco, SubAreaUnesco
from sga.commonviews import adduserdata
from sga.forms import PropuestaLineaInvestigacionForm, PropuestaSubLineaInvestigacionForm
from investigacion.forms import AreaUnescoForm
from sga.funciones import log, generar_nombre, MiPaginador
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import PropuestaLineaInvestigacion, PropuestaTitulacion, \
    PropuestaSubLineaInvestigacion, PropuestaLineaInvestigacion_Carrera, Carrera, Coordinacion, \
    PropuestaSubLineaInvestigacionCarrera, PropuestaLineaInvestigacionResolucion
from sga.templatetags.sga_extras import encrypt
from django.template.loader import get_template
from django.contrib import messages

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        # LINEA
        if action == 'addlinea':
            try:
                if 'lista_items1' not in request.POST and 'lista_items2' not in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe agregar por lo menos una carrera de pregrado o programa de posgrado"})

                form = PropuestaLineaInvestigacionForm(request.POST, request.FILES)
                if form.is_valid():
                    carreraspregrado = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else None
                    carrerasposgrado = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else None

                    # if not form.cleaned_data['carreras']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos una carrera"})

                    if not PropuestaLineaInvestigacion.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        # Guardo línea de investigación
                        lineainvestigacion = PropuestaLineaInvestigacion(
                                nombre=form.cleaned_data['nombre'],

                                # numeroresolucion=form.cleaned_data['numeroresolucion'],

                                contexto=form.cleaned_data['contexto'],
                                descripcion=form.cleaned_data['descripcion'],
                                campoaccion_id=form.cleaned_data['campoaccion'] if form.cleaned_data['campoaccion'] > 0 else None,
                                areaunesco=form.cleaned_data['areaunesco'],
                                alcance=form.cleaned_data['alcance']

                                # facultad=form.cleaned_data['facultad'],

                                # fecharesolucion=form.cleaned_data['fecharesolucion']

                        )
                        lineainvestigacion.save(request)

                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("propuestaresolucion", newfile._name)

                        # Guardo la resolución
                        resolucion = PropuestaLineaInvestigacionResolucion(
                            linea=lineainvestigacion,
                            numero=form.cleaned_data['numeroresolucion'],
                            fecha=form.cleaned_data['fecharesolucion'],
                            archivo=newfile,
                            vigente=True,
                            tipo=1
                        )
                        resolucion.save(request)

                        # Guardo carreras de pregrado
                        if carreraspregrado:
                            for detalle in carreraspregrado:
                                lineacarrera = PropuestaLineaInvestigacion_Carrera(
                                    linea=lineainvestigacion,
                                    coordinacion_id=detalle['facultad'],
                                    carrera_id=detalle['carrera']
                                )
                                lineacarrera.save(request)

                        # Guardo programas de posgrado
                        if carrerasposgrado:
                            for detalle in carrerasposgrado:
                                lineacarrera = PropuestaLineaInvestigacion_Carrera(
                                    linea=lineainvestigacion,
                                    coordinacion_id=detalle['facultad'],
                                    carrera_id=detalle['carrera']
                                )
                                lineacarrera.save(request)


                        # if 'archivo' in request.FILES:
                        #     newfile = request.FILES['archivo']
                        #     newfile._name = generar_nombre("propuestaresolucion", newfile._name)
                        #     lineainvestigacion.archivo = newfile
                        #     lineainvestigacion.save(request)

                        # for car in form.cleaned_data['carreras']:
                        #     carrera=PropuestaLineaInvestigacion_Carrera(linea=lineainvestigacion,carrera=car)
                        #     carrera.save(request)

                        log(u'Agrego Propuesta de Línea de Investigación: %s' % lineainvestigacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre de la línea de investitación ya existe."})
                else:
                    x = form.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'editlinea':
            try:
                if 'lista_items1' not in request.POST and 'lista_items2' not in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe agregar por lo menos una carrera de pregrado o programa de posgrado"})

                form = PropuestaLineaInvestigacionForm(request.POST, request.FILES)
                if form.is_valid():
                    carreraspregrado = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else None
                    carrerasposgrado = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else None

                    # if not form.cleaned_data['carreras']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos una carrera"})
                    #
                    if not PropuestaLineaInvestigacion.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        # Consulto y Actualizo datos de la línea
                        linea = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                        linea.nombre = form.cleaned_data['nombre']

                        # linea.numeroresolucion = form.cleaned_data['numeroresolucion']
                        # linea.fecharesolucion = form.cleaned_data['fecharesolucion']
                        #
                        linea.contexto = form.cleaned_data['contexto']
                        linea.descripcion = form.cleaned_data['descripcion']
                        linea.campoaccion_id = form.cleaned_data['campoaccion'] if form.cleaned_data['campoaccion'] > 0 else None
                        linea.areaunesco = form.cleaned_data['areaunesco']
                        linea.alcance = form.cleaned_data['alcance']

                        # linea.facultad = form.cleaned_data['facultad']

                        linea.save(request)

                        # Consulto y Actualizo datos de la resolución
                        resolucionlinea = linea.resolucion_vigente()
                        resolucionlinea.numero = form.cleaned_data['numeroresolucion']
                        resolucionlinea.fecha = form.cleaned_data['fecharesolucion']
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("propuestaresolucion", newfile._name)
                            resolucionlinea.archivo = newfile

                        resolucionlinea.save(request)

                        # En caso que haya borrado todos los detalles de pregrado
                        if not carreraspregrado:
                            for carreralinea in linea.detalle_carreras_pregrado():
                                carreralinea.status = False
                                carreralinea.save(request)

                        # En caso que haya borrado todos los detalles de posgrado
                        if not carrerasposgrado:
                            for carreralinea in linea.detalle_carreras_posgrado():
                                carreralinea.status = False
                                carreralinea.save(request)

                        # Guardar y eliminar detalles de pregrado
                        if carreraspregrado:
                            # Obtengo los ids de detalles de pregrado
                            lista_id = [detalle['iddetalle'] for detalle in carreraspregrado if detalle['iddetalle'] > 0]
                            # Elimino los detalles de carrera de pregrado
                            for lineacarrera in linea.propuestalineainvestigacion_carrera_set.filter(status=True, carrera__niveltitulacion__id=3).exclude(pk__in=lista_id):
                                lineacarrera.status = False
                                lineacarrera.save(request)

                            # Guardo los detalles de carrera nuevos de pregrado
                            for detalle in carreraspregrado:
                                if detalle['iddetalle'] == 0:
                                    lineacarrera = PropuestaLineaInvestigacion_Carrera(
                                        linea=linea,
                                        coordinacion_id=detalle['facultad'],
                                        carrera_id=detalle['carrera']
                                    )
                                    lineacarrera.save(request)

                        # Guardar y eliminar detalles de posgrado
                        if carrerasposgrado:
                            # Obtengo los ids de detalles de posgrado
                            lista_id = [detalle['iddetalle'] for detalle in carrerasposgrado if detalle['iddetalle'] > 0]
                            # Elimino los detalles de carrera de posgrado
                            for lineacarrera in linea.propuestalineainvestigacion_carrera_set.filter(status=True, carrera__niveltitulacion__id=4).exclude(pk__in=lista_id):
                                lineacarrera.status = False
                                lineacarrera.save(request)

                            # Guardo los detalles de carrera nuevos de posgrado
                            for detalle in carrerasposgrado:
                                if detalle['iddetalle'] == 0:
                                    lineacarrera = PropuestaLineaInvestigacion_Carrera(
                                        linea=linea,
                                        coordinacion_id=detalle['facultad'],
                                        carrera_id=detalle['carrera']
                                    )
                                    lineacarrera.save(request)


                        # for carrera in form.cleaned_data['carreras']:
                        #     if not PropuestaLineaInvestigacion_Carrera.objects.filter(linea_id=linea.id,carrera=carrera).exists():
                        #         lineacarrera = PropuestaLineaInvestigacion_Carrera(linea_id=linea.id, carrera_id=carrera.id)
                        #         lineacarrera.save(request)
                        #         log(u'Edito Propuesta de Línea de Investigación Carrera: %s [%s]' % (lineacarrera, lineacarrera.id), request, "edit")
                        #
                        # if linea.propuestalineainvestigacion_carrera_set.all().exclude(carrera__in = form.cleaned_data['carreras']):
                        #     for carrera in linea.propuestalineainvestigacion_carrera_set.all().exclude(carrera__in = form.cleaned_data['carreras']):
                        #         log(u'Eliminó Propuesta de Línea de Investigación Carrera: %s [%s]- %s[%s]' % (carrera.carrera, carrera.carrera.id, carrera.linea, carrera.linea.id), request, "del")
                        #     linea.propuestalineainvestigacion_carrera_set.all().exclude(carrera__in = form.cleaned_data['carreras']).delete()

                        # if 'archivo' in request.FILES:
                        #     newfile = request.FILES['archivo']
                        #     newfile._name = generar_nombre("propuestaresolucion", newfile._name)
                        #     linea.archivo = newfile
                        #     linea.save(request)
                        log(u'Edito Propuesta de Línea de Investigación: %s' % linea, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre de la línea de investitación ya existe."})
                else:
                    x = form.errors
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'carrerascoordinacion':
            try:
                facultad = Coordinacion.objects.get(pk=request.POST['id'])
                lista = []
                for carrera in facultad.carreras().filter(niveltitulacion__isnull=False):
                    lista.append([carrera.id, carrera.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'actualizarresolucion':
            try:
                if not 'idlinea' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                lineainvestigacion = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.POST['idlinea'])))

                archivo = request.FILES['archivoresolucion']
                archivo._name = generar_nombre("propuestaresolucion", archivo._name)

                # Pongo estado no vigente a las resoluciones existentes
                for resolucion in lineainvestigacion.resoluciones():
                    resolucion.vigente = False
                    resolucion.save(request)

                # Guardo la nueva resolución
                resolucion = PropuestaLineaInvestigacionResolucion(
                    linea=lineainvestigacion,
                    numero=request.POST['numeroresolucion'].strip().upper(),
                    fecha=datetime.strptime(request.POST['fecharesolucion'].strip(), "%d-%m-%Y").date(),
                    archivo=archivo,
                    vigente=True,
                    tipo=2
                )
                resolucion.save(request)

                log(u'Actualizó resolución de línea de investigación: %s' % (lineainvestigacion), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action =='dellinea':
            try:
                linea = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                if not linea.puede_eliminar():
                    return JsonResponse({"result": "bad","mensaje": u"No puede eliminarse, se esta ocupando en Propuesta o tiene SubLíneas."})
                linea.delete()
                log(u'Elimino Propuesta de Línea de Investigación: %s' % linea, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'darbajalinea':
            try:
                linea = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                if linea.activo:
                    linea.activo = False
                    log(u'Desactivo la Propuesta de Línea de Investigación: %s' % linea, request, "darbaja")
                else:
                    linea.activo = True
                    log(u'Activo la Propuesta de Línea de Investigación: %s' % linea, request, "darbaja")
                linea.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # SUBLINEA
        elif action == 'addsub':
            try:
                form = PropuestaSubLineaInvestigacionForm(request.POST)
                if form.is_valid():
                        if not PropuestaSubLineaInvestigacion.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                            sublinea=PropuestaSubLineaInvestigacion(nombre=form.cleaned_data['nombre'],
                                                                    contexto=form.cleaned_data['contexto'],
                                                                    descripcion=form.cleaned_data['descripcion'],
                                                                    subareaunesco=form.cleaned_data['subarea'],
                                                                    linea_id=int(encrypt(request.POST['id'])))
                            sublinea.save(request)
                            PropuestaSubLineaInvestigacionCarrera.objects.filter(propuestasublineainvestigacion=sublinea).delete()
                            carreras = form.cleaned_data['carreras']
                            for carrera in carreras:
                                propuestasublineainvestigacioncarrera = PropuestaSubLineaInvestigacionCarrera(propuestasublineainvestigacion=sublinea, carrera=carrera)
                                propuestasublineainvestigacioncarrera.save(request)
                            log(u'Agrego Propuesta de SubLínea de Investigación: %s' % sublinea, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action =='editsub':
            try:
                form = PropuestaSubLineaInvestigacionForm(request.POST)
                if form.is_valid():
                    sublinea = PropuestaSubLineaInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    sublinea.nombre=form.cleaned_data['nombre']
                    sublinea.contexto=form.cleaned_data['contexto']
                    sublinea.subareaunesco=form.cleaned_data['subarea']
                    sublinea.descripcion=form.cleaned_data['descripcion']
                    sublinea.save(request)
                    sublinea.propuestasublineainvestigacioncarrera_set.all().delete()
                    carreras = form.cleaned_data['carreras']
                    for carrera in carreras:
                        propuestasublineainvestigacioncarrera = PropuestaSubLineaInvestigacionCarrera(propuestasublineainvestigacion=sublinea, carrera=carrera)
                        propuestasublineainvestigacioncarrera.save(request)
                    log(u'Editar Propuesta de SubLínea de Investigación: %s' % sublinea, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action =='delsub':
            try:
                sublinea = PropuestaSubLineaInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                if not sublinea.puede_eliminar():
                    return JsonResponse({"result": "bad","mensaje": u"No se puede Eliminar el Periodo de Titulacion, tiene Grupos de Titulacion Activas.."})
                sublinea.delete()
                log(u'Elimino Propuesta de SubLínea de Investigación: %s' % sublinea, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'darbajasub':
            try:
                sublinea = PropuestaSubLineaInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                if sublinea.activo:
                    sublinea.activo = False
                    log(u'Desactivo la Propuesta de SubLínea de Investigación: %s' % sublinea, request, "darbaja")
                else:
                    sublinea.activo = True
                    log(u'Activo la Propuesta de SubLínea de Investigación: %s' % sublinea, request, "darbaja")
                sublinea.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcarrera':
            try:
                form = PropuestaSubLineaInvestigacionForm(request.POST)
                sublinea = PropuestaSubLineaInvestigacion.objects.filter(pk=request.POST['id']).first()
                form.addcarrera(sublinea.carreras().values_list('carrera_id', flat=True))
                if form.is_valid():
                    for c in form.cleaned_data['carreras']:
                        sublineacarrera = PropuestaSubLineaInvestigacionCarrera(propuestasublineainvestigacion=sublinea, carrera=c)
                        sublineacarrera.save(request)
                    log('Adicionó carreras en SubLinea %s' % sublinea, request, 'add')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action =='delcarrera':
            try:
                sublineacarrera = PropuestaSubLineaInvestigacionCarrera.objects.get(pk=int(encrypt(request.POST['id'])))
                sublineacarrera.delete()
                log(u'Elimino Carrera de Propuesta de SubLínea de Investigación: %s' % sublineacarrera.propuestasublineainvestigacion, request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addareaunesco':
            try:
                f = AreaUnescoForm(request.POST)
                if f.is_valid():
                    if AreaUnesco.objects.values('id').filter(nombre=f.cleaned_data['nombre'].strip(),status=True).exists():
                        raise NameError(u'El registro ya existe.')
                    areaunesco = AreaUnesco(nombre=f.cleaned_data['nombre'])
                    areaunesco.save(request)
                    log(u'Adiciono nueva Área: %s' % areaunesco, request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editareaunesco':
            try:
                with transaction.atomic():
                    areaunesco = AreaUnesco.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = AreaUnescoForm(request.POST)
                    if f.is_valid():
                        if not AreaUnesco.objects.values('id').filter(nombre=f.cleaned_data['nombre']).exists():
                            areaunesco.nombre = f.cleaned_data['nombre']
                            areaunesco.save(request)
                            log(u'Modificó Área: %s' % areaunesco, request, "edit")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'deleteareaunesco':
            try:
                with transaction.atomic():
                    areaunesco = AreaUnesco.objects.get(pk=int(encrypt(request.POST['id'])))
                    areaunesco.status = False
                    areaunesco.save()
                    log(u'Eliminó Área: %s' % areaunesco, request, "del")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addsubareaunesco':
            try:
                f = AreaUnescoForm(request.POST)
                if f.is_valid():
                    areaunesco=AreaUnesco.objects.get(pk=int(encrypt(request.POST['id'])))
                    if SubAreaUnesco.objects.values('id').filter(nombre=f.cleaned_data['nombre'].strip(),status=True,cabarea=areaunesco).exists():
                        raise NameError(u'El registro ya existe.')
                    subareaunesco = SubAreaUnesco(nombre=f.cleaned_data['nombre'],cabarea=areaunesco)
                    subareaunesco.save(request)
                    log(u'Adiciono nueva Área: %s' % subareaunesco, request, "add")
                    messages.success(request, 'Registro guardado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editsubareaunesco':
            try:
                with transaction.atomic():
                    subareaunesco = SubAreaUnesco.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = AreaUnescoForm(request.POST)
                    if f.is_valid():
                        if not SubAreaUnesco.objects.values('id').filter(nombre=f.cleaned_data['nombre']).exists():
                            subareaunesco.nombre = f.cleaned_data['nombre']
                            subareaunesco.save(request)
                            log(u'Modificó sub Área: %s' % subareaunesco, request, "edit")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'deletesubareaunesco':
            try:
                with transaction.atomic():
                    subareaunesco = SubAreaUnesco.objects.get(pk=int(encrypt(request.POST['id'])))
                    subareaunesco.status = False
                    subareaunesco.save()
                    log(u'Eliminó Área: %s' % subareaunesco, request, "del")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addlinea':
                try:
                    data['title'] = u'Adicionar Línea de Investigación'
                    form = PropuestaLineaInvestigacionForm()
                    data['facultadespregrado'] = Coordinacion.objects.filter(status=True, pk__lte=5).order_by('nombre')
                    data['facultadesposgrado'] = Coordinacion.objects.filter(status=True, pk=7).order_by('nombre')
                    # form.fields['carreras'].queryset = Carrera.objects.none()
                    data['form'] = form
                    return render(request, "adm_propuestalineainvestigacion/addlinea.html", data)
                except Exception as ex:
                    pass

            elif action == 'actualizarresolucion':
                try:
                    data['title'] = u'Actualizar Resolución de la Línea'
                    lineainvestigacion = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    return JsonResponse({"result": "ok", 'title': data['title'], 'nombrelinea': lineainvestigacion.nombre})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarresoluciones':
                try:
                    data['title'] = u'Resoluciones de la Línea de investigación'
                    lineainvestigacion = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    resoluciones = [{"numero": resolucion.numero,
                                     "fecha": resolucion.fecha,
                                     "archivo": resolucion.archivo.url} for resolucion in lineainvestigacion.resoluciones()]

                    return JsonResponse({"result": "ok", 'title': data['title'], 'nombrelinea': lineainvestigacion.nombre, 'resoluciones': resoluciones})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'reportelineas':
                try:
                    data = {}
                    data['fechaactual'] = datetime.now()
                    data['det'] = det = PropuestaLineaInvestigacion.objects.filter(status=True).order_by('nombre')
                    data['numlineas'] = det.count()
                    return conviert_html_to_pdf('adm_propuestalineainvestigacion/reportelineas.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            elif action == 'reportelineasanio':
                try:
                    data = {}
                    data['fechaactual'] = datetime.now()
                    data['anoaprobacion'] = anio = request.GET['anio']
                    data['det'] = det = PropuestaLineaInvestigacion.objects.filter(fecharesolucion__year=anio,status=True).order_by('nombre')
                    data['numlineas'] = det.count()
                    return conviert_html_to_pdf('adm_propuestalineainvestigacion/reportelineasanio.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            elif action == 'reportesublineas':
                try:
                    data = {}
                    data['fechaactual'] = datetime.now()
                    data['det'] = det = PropuestaSubLineaInvestigacion.objects.filter(status=True).order_by('linea__nombre')
                    data['numlineas'] = det.count()
                    return conviert_html_to_pdf('adm_propuestalineainvestigacion/reportesublineas.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            elif action == 'reportesublineasanio':
                try:
                    data = {}
                    data['fechaactual'] = datetime.now()
                    data['anoaprobacion'] = anio = request.GET['anio']
                    data['det'] = det = PropuestaSubLineaInvestigacion.objects.filter(linea__fecharesolucion__year=anio,status=True).order_by('linea__nombre')
                    data['numlineas'] = det.count()
                    return conviert_html_to_pdf('adm_propuestalineainvestigacion/reportesublineasanio.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            elif action == 'reportefacultad':
                try:
                    data = {}
                    data['fechaactual'] = datetime.now()
                    data['facultad'] = facultad = Coordinacion.objects.filter(pk=int(encrypt(request.GET['facultad'])))[0]
                    data['det'] = det = PropuestaLineaInvestigacion.objects.filter(facultad__pk=int(encrypt(request.GET['facultad'])),status=True).order_by('nombre')
                    data['numsublineas'] = PropuestaSubLineaInvestigacion.objects.filter(linea__facultad__pk=int(encrypt(request.GET['facultad'])),status=True).count()
                    data['numlineas'] = det.count()
                    return conviert_html_to_pdf('adm_propuestalineainvestigacion/reportelineasfacultad.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            elif action == 'reportecarrera':
                try:
                    data = {}
                    data['fechaactual'] = datetime.now()
                    data['carrera'] = carrrera = Carrera.objects.filter(pk=int(encrypt(request.GET['carreras'])))[0]
                    data['det'] = det = PropuestaLineaInvestigacion_Carrera.objects.filter(carrera__pk=int(encrypt(request.GET['carreras'])),status=True).order_by('linea__nombre')
                    if det:
                        cont = PropuestaSubLineaInvestigacion.objects.filter(linea=det[0].linea,status=True).count()
                    else:
                        cont = 0
                    data['numsublineas'] = cont
                    data['numlineas'] = det.count()
                    return conviert_html_to_pdf('adm_propuestalineainvestigacion/reportelineascarreras.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            elif action == 'consultacarreras':
                id = int(request.GET['id'])
                carrera = Coordinacion.objects.get(pk=int(id))
                #carrera2 = Carrera.objects.filter(status=True, coordinacionvalida__pk=int(id), activa=True).order_by('pk')
                resp = [{'id': cr.pk, 'text': cr.nombre} for cr in carrera.carreras() if cr.status and cr.activa]
                return HttpResponse(json.dumps({'state': True, 'result': resp}))

            elif action == 'consultacarrerasreporte':
                id = int(encrypt(request.GET['id']))
                carrera = Coordinacion.objects.get(pk=int(id))
                #carrera2 = Carrera.objects.filter(status=True, coordinacionvalida__pk=int(id), activa=True).order_by('pk')
                resp = [{'id': encrypt(cr.pk), 'text': cr.nombre} for cr in carrera.carreras() if cr.status and cr.activa]
                return HttpResponse(json.dumps({'state': True, 'result': resp}))

            elif action == 'busquedacampoaccion':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        campo = InvCabAreas.objects.filter(Q(nombre__icontains=s[0])).filter(status=True).distinct()[:15]
                    else:
                        campo = InvCabAreas.objects.filter(Q(nombre__icontains=s[0])).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.nombre} for x in campo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'busquedaareaunesco':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        area = AreaUnesco.objects.filter(Q(nombre__icontains=s[0])).filter(status=True).distinct()[:15]
                    else:
                        area = AreaUnesco.objects.filter(Q(nombre__icontains=s[0])).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.nombre} for x in area]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'dellinea':
                try:
                    data['title'] = u'Eliminar Línea de Investigación'
                    data['linea'] = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_propuestalineainvestigacion/dellinea.html", data)
                except Exception as ex:
                    pass

            elif action == 'darbajalinea':
                try:
                    data['title'] = u'Dar de Baja Línea de Investigación'
                    data['linea'] = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_propuestalineainvestigacion/darbajalinea.html", data)
                except Exception as ex:
                    pass

            elif action == 'editlinea':
                try:
                    data['title'] = u'Editar Línea de Investigación'
                    data['linea'] = linea = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    resolucion = linea.resolucion_vigente()
                    form = PropuestaLineaInvestigacionForm(initial={'nombre': linea.nombre,
                                                                    'numeroresolucion': resolucion.numero,
                                                                    'fecharesolucion': resolucion.fecha,
                                                                    'contexto': linea.contexto,
                                                                    'descripcion': linea.descripcion,
                                                                    'alcance': linea.alcance,
                                                                    'areaunesco': linea.areaunesco
                                                                    # 'facultad': linea.facultad,
                                                                    # 'carreras': Carrera.objects.filter(pk__in=[carrera.carrera.id  for carrera in linea.propuestalineainvestigacion_carrera_set.all()])
                                                                    })

                    if linea.campoaccion:
                        form.editar(linea)
                        form.fields['campoaccion'].initial = linea.campoaccion.pk

                    data['form'] = form
                    data['facultadespregrado'] = Coordinacion.objects.filter(status=True, pk__lte=5).order_by('nombre')
                    data['facultadesposgrado'] = Coordinacion.objects.filter(status=True, pk=7).order_by('nombre')
                    data['carreraspregrado'] = linea.detalle_carreras_pregrado()
                    data['carrerasposgrado'] = linea.detalle_carreras_posgrado()

                    return render(request, "adm_propuestalineainvestigacion/editlinea.html", data)
                except Exception as ex:
                    pass

            # SUBLINEA
            elif action == 'addsub':
                try:
                    data['title'] = u'SubLínea de Investigación'
                    data['linea'] = linea = PropuestaLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    form=PropuestaSubLineaInvestigacionForm(initial={'linea':linea})
                    form.fields['subarea'].queryset = SubAreaUnesco.objects.filter(cabarea=linea.areaunesco)
                    data['form'] = form
                    form.editarlinea()
                    data['form'] = form
                    return render(request, "adm_propuestalineainvestigacion/addsub.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsub':
                try:
                    data['title'] = u'Eliminar SubLínea de Investigación'
                    data['sublinea'] = PropuestaSubLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_propuestalineainvestigacion/delsub.html", data)
                except Exception as ex:
                    pass

            elif action == 'darbajasub':
                try:
                    data['title'] = u'Dar de Baja SubLínea de Investigación'
                    data['sublinea'] = PropuestaSubLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_propuestalineainvestigacion/darbajasub.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsub':
                    try:
                        data['title'] = u'Editar SubLínea de Investigación'
                        data['sublinea'] = sublinea = PropuestaSubLineaInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        idcarreras = sublinea.propuestasublineainvestigacioncarrera_set.values_list('carrera_id', flat=True).filter(status=True)
                        carreras = Carrera.objects.filter(pk__in=idcarreras)
                        form = PropuestaSubLineaInvestigacionForm(initial={'nombre':sublinea.nombre,
                                                                           'linea':sublinea.linea,
                                                                           'contexto':sublinea.contexto,
                                                                           'descripcion':sublinea.descripcion,
                                                                           'subarea':sublinea.subareaunesco,
                                                                           'carreras': carreras})
                        form.editarlinea()
                        data['form'] = form
                        return render(request, "adm_propuestalineainvestigacion/editsub.html", data)
                    except Exception as ex:
                        pass

            elif action == 'viewsub':
                    try:
                        data['title'] = u'SubLínea de Investigación'
                        data['sublinea'] = PropuestaSubLineaInvestigacion.objects.filter(linea_id=int(encrypt(request.GET['id'])),status=True)
                        data['linea'] = PropuestaLineaInvestigacion.objects.get(id=int(encrypt(request.GET['id'])),status=True)
                        return render(request, "adm_propuestalineainvestigacion/viewsub.html", data)
                    except Exception as ex:
                        pass

            elif action == 'carreras':
                try:
                    if 'id' in request.GET:
                        if request.GET['id']:
                            sublinea = PropuestaSubLineaInvestigacion.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                            if sublinea:
                                data['title'] = u'%s' % sublinea.nombre
                                data['sublinea'] = sublinea
                                return render(request, "adm_propuestalineainvestigacion/carreras.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcarrera':
                try:
                    if request.GET['id']:
                        sublinea = PropuestaSubLineaInvestigacion.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                        form = PropuestaSubLineaInvestigacionForm()
                        form.addcarrera(sublinea.carreras().values_list('carrera_id', flat=True))
                        data['form'] = form
                        data['id'] = sublinea.pk
                        data['action'] = action
                        template = get_template("adm_propuestalineainvestigacion/modal/form.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            elif action == 'areaunesco':
                try:
                    data['title'] = u'Gestión de Áreas y Subáreas Unesco'
                    search = None
                    ids = None
                    areas = AreaUnesco.objects.filter(status=True).order_by('pk')
                    if 's' in request.GET:
                        search = request.GET['s']
                        areas = areas.filter(Q(nombre__icontains=search)).order_by('pk')
                    elif 'id' in request.GET:
                        ids = int(encrypt(request.GET['id']))
                        areas = areas.filter(id=ids).order_by('pk')
                    paging = MiPaginador(areas, 20)
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
                    data['ids'] = ids if ids else ""
                    data['lista'] = page.object_list
                    return render(request, "adm_propuestalineainvestigacion/areainv/viewareasunesco.html", data)
                except Exception as ex:
                    pass

            elif action == 'addareaunesco':
                try:
                    form = AreaUnescoForm()
                    data['action'] = 'addareaunesco'
                    data['form'] = form
                    template = get_template("adm_propuestalineainvestigacion/modal/formareaunesco.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editareaunesco':
                try:
                    data['action'] = 'editareaunesco'
                    data['id'] = int(encrypt(request.GET['id']))
                    data['areaunesco'] = areaunesco = AreaUnesco.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = AreaUnescoForm(initial={'nombre': areaunesco.nombre})
                    data['form'] = form
                    template = get_template("adm_propuestalineainvestigacion/modal/formareaunesco.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'subareaunesco':
                try:
                    data['title'] = u'Gestión de Sub ubáreas Unesco'
                    search = None
                    ids = None
                    data['area'] =area= AreaUnesco.objects.get(id=int(encrypt(request.GET['ida'])))
                    subareas = SubAreaUnesco.objects.filter(status=True,cabarea=area).order_by('pk')
                    if 's' in request.GET:
                        search = request.GET['s']
                        subareas = subareas.filter(Q(nombre__icontains=search)).order_by('pk')
                    elif 'id' in request.GET:
                        ids = int(encrypt(request.GET['id']))
                        subareas = subareas.filter(id=ids).order_by('pk')
                    paging = MiPaginador(subareas, 20)
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
                    data['ids'] = ids if ids else ""
                    data['lista'] = page.object_list
                    return render(request, "adm_propuestalineainvestigacion/subareainv/viewsubareasunesco.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsubareaunesco':
                try:
                    form = AreaUnescoForm()
                    data['id'] = int(encrypt(request.GET['idp']))
                    data['areaunesco'] = areaunesco = AreaUnesco.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['action'] = 'addsubareaunesco'
                    data['form'] = form
                    template = get_template("adm_propuestalineainvestigacion/modal/formareaunesco.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editsubareaunesco':
                try:
                    data['action'] = 'editsubareaunesco'
                    data['id'] = int(encrypt(request.GET['id']))
                    data['subareaunesco'] = subareaunesco = SubAreaUnesco.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = AreaUnescoForm(initial={'nombre': subareaunesco.nombre})
                    data['form'] = form
                    template = get_template("adm_propuestalineainvestigacion/modal/formareaunesco.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Línea de Investigación'
                search = None
                ids = None
                tipobus = 0

                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    linea = PropuestaLineaInvestigacion.objects.filter(Q(nombre__icontains=search)).filter(status=True).order_by('nombre')
                elif 'id' in request.GET:
                    ids = encrypt(request.GET['id'])
                    linea = PropuestaLineaInvestigacion.objects.filter(id=ids, status=True).order_by('nombre')
                else:
                    linea = PropuestaLineaInvestigacion.objects.filter(status=True).order_by('nombre')

                if 'tipobus' in request.GET:
                    tipobus = int(request.GET['tipobus'])
                    if tipobus > 0:
                        linea = linea.filter(activo=True) if tipobus == 1 else linea.filter(activo=False)

                data['tipobus'] = tipobus

                paging = MiPaginador(linea, 30)
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
                data['ids'] = ids if ids else ""
                data['linea'] = page.object_list
                date = list(PropuestaLineaInvestigacion.objects.filter(status=True).distinct('fecharesolucion').order_by('fecharesolucion').values_list('fecharesolucion',flat=True))
                data['aniosejercicio'] = sorted(set([ l2[0] for l2 in [ str(l).split('-') for l in date ]]))
                data['facultad'] = Coordinacion.objects.filter(status=True,id__in=list(Carrera.objects.filter(~Q(coordinacionvalida=None),status=True, activa=True).distinct('coordinacionvalida_id').order_by('coordinacionvalida_id').values_list('coordinacionvalida_id', flat=True)))
                return render(request, "adm_propuestalineainvestigacion/viewlinea.html", data)
            except Exception as ex:
                pass