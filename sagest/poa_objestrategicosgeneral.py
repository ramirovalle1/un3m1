# -*- coding: UTF-8 -*-

import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext,Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import ObjetivoEstrategicoForm, DocumentosIndicadorPoaForm
from sagest.models import ObjetivoEstrategico, PeriodoPoa, Departamento, AccionDocumento, TIPO_ACCION, \
    MedioVerificacion, IndicadorPoa, ObjetivoOperativo, ObjetivoTactico, ProgramaPoa, DistributivoPersona
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador,log



from sga.models import Carrera

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'adicionarestrategico':
            try:
                if request.POST['id_carrera'] == '0':
                    carrera = ''
                else:
                    carrera = request.POST['id_carrera']
                estrategicos = ObjetivoEstrategico(periodopoa_id=request.POST['id_periodopoa'],
                                                   departamento_id=request.POST['id_departamento'],
                                                   programa_id=request.POST['id_programa'],
                                                   descripcion=request.POST['id_descripcion'],
                                                   orden=request.POST['id_orden'],
                                                   carrera_id=carrera
                                                   )
                log(u'elimino detalles documento a poa: %s' % estrategicos, request, "add")
                estrategicos.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'duplicar':
            try:
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['idperiodopoa'])
                if request.POST['idcarrera'] == '0':
                    carrera = None
                else:
                    carrera = Carrera.objects.get(pk=request.POST['idcarrera'])
                iddepartamento = request.POST['iddepartamento']
                iddepartamentoelejido = request.POST['iddepartamentoelejido']
                cadena = iddepartamentoelejido.split('_')
                departamento = Departamento.objects.get(pk=cadena[0])
                if request.POST['idcarrera'] == '0':
                    if ObjetivoEstrategico.objects.filter(periodopoa=periodopoa, departamento_id=iddepartamento, carrera__isnull=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": "Ya existe departamento y carrera a ingresar"})
                else:
                    if ObjetivoEstrategico.objects.filter(periodopoa=periodopoa, departamento_id=iddepartamento, carrera=carrera).exists():
                        return JsonResponse({"result": "bad", "mensaje": "Ya existe departamento y carrera a ingresar"})
                for p in PeriodoPoa.objects.filter(pk=request.POST['idperiodopoa']):
                    if cadena[1] == '0':
                        for oe in p.objetivoestrategico_set.filter(departamento=departamento, carrera__isnull=True):
                            aux_oe = oe.objetivotactico_set.all()
                            oe.id = None
                            oe.periodopoa = periodopoa
                            oe.departamento_id = iddepartamento
                            if request.POST['idcarrera'] == '0':
                                oe.carrera_id = None
                            else:
                                oe.carrera = carrera
                            oe.save(request)
                            for ot in aux_oe:
                                aux_ot = ot.objetivooperativo_set.all()
                                ot.id = None
                                ot.objetivoestrategico = oe
                                ot.save(request)
                                for oo in aux_ot:
                                    aux_oo = oo.indicadorpoa_set.all()
                                    oo.id = None
                                    oo.objetivotactico = ot
                                    oo.save(request)
                                    for i in aux_oo:
                                        aux_i = i.acciondocumento_set.all()
                                        i.id = None
                                        i.objetivooperativo = oo
                                        i.save(request)
                                        for ad in aux_i:
                                            aux_ad = ad.acciondocumentodetalle_set.all()
                                            ad.id = None
                                            ad.indicadorpoa = i
                                            ad.save(request)
                                            for acd in aux_ad:
                                                # aux_acd = acd.acciondocumentodetallerecord_set.all()
                                                acd.id = None
                                                acd.acciondocumento = ad
                                                acd.save(request)
                        log(u'Duplico objetivo estrategico general: %s' % oe, request, "add")
                                                # for adr in aux_acd:
                                                #     adr.id = None
                                                #     adr.acciondocumentodetalle = acd
                                                #     adr.save(request)
                    else:
                        for oe in p.objetivoestrategico_set.filter(departamento=departamento, carrera_id=cadena[1]):
                            aux_oe = oe.objetivotactico_set.all()
                            oe.id = None
                            oe.periodopoa = periodopoa
                            oe.departamento_id = iddepartamento
                            if request.POST['idcarrera'] == '0':
                                oe.carrera_id = None
                            else:
                                oe.carrera = carrera
                            oe.save(request)
                            for ot in aux_oe:
                                aux_ot = ot.objetivooperativo_set.all()
                                ot.id = None
                                ot.objetivoestrategico = oe
                                ot.save(request)
                                for oo in aux_ot:
                                    aux_oo = oo.indicadorpoa_set.all()
                                    oo.id = None
                                    oo.objetivotactico = ot
                                    oo.save(request)
                                    for i in aux_oo:
                                        aux_i = i.acciondocumento_set.all()
                                        i.id = None
                                        i.objetivooperativo = oo
                                        i.save(request)
                                        for ad in aux_i:
                                            aux_ad = ad.acciondocumentodetalle_set.all()
                                            ad.id = None
                                            ad.indicadorpoa = i
                                            ad.save(request)
                                            for acd in aux_ad:
                                                aux_acd = acd.acciondocumentodetallerecord_set.all()
                                                acd.id = None
                                                acd.acciondocumento = ad
                                                acd.save(request)
                                                for adr in aux_acd:
                                                    adr.id = None
                                                    adr.acciondocumentodetalle = acd
                                                    adr.save(request)
                        log(u'Duplico objetivo estrategico general: %s' % oe, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al procesar el traspaso."})

        if action == 'listaacciones':
            try:
                acciones = AccionDocumento.objects.get(pk=request.POST['id'])
                descripcion = acciones.descripcion
                codigoaccion = acciones.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigoaccion': codigoaccion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'listaindicadores':
            try:
                indicador = IndicadorPoa.objects.get(pk=request.POST['id'])
                descripcion = indicador.descripcion
                codigoindicador = indicador.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigoindicador': codigoindicador})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'listaoperativos':
            try:
                operativo = ObjetivoOperativo.objects.get(pk=request.POST['id'])
                descripcion = operativo.descripcion
                codigooperativo = operativo.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigooperativo': codigooperativo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'listatacticos':
            try:
                tactico = ObjetivoTactico.objects.get(pk=request.POST['id'])
                descripcion = tactico.descripcion
                codigotactico = tactico.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigotactico': codigotactico})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminaracciones':
            try:
                acciones = AccionDocumento.objects.get(pk=request.POST['codigoaccion'])
                acciones.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'eliminarindicadores':
            try:
                indicador = IndicadorPoa.objects.get(pk=request.POST['codigoindicadordel'])
                indicador.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'eliminaroperativos':
            try:
                operativo = ObjetivoOperativo.objects.get(pk=request.POST['codigooperativodel'])
                operativo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'eliminartacticos':
            try:
                tactico = ObjetivoTactico.objects.get(pk=request.POST['codigotacticodel'])
                tactico.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'consultaraccion':
            try:
                acciones = AccionDocumento.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'idaccion': acciones.id, 'orden': acciones.orden, 'nombre': acciones.descripcion, 'tipo': acciones.tipo, 'medioverificacion': acciones.medioverificacion_id, 'observacion': acciones.observacion, 'enlace': acciones.enlace, 'porcentaje': acciones.porcentaje.__str__()})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        if action == 'consultarindicador':
            try:
                indicador = IndicadorPoa.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'idindicador': indicador.id, 'orden': indicador.orden, 'nombre': indicador.descripcion})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        if action == 'consultaroperativo':
            try:
                operativo = ObjetivoOperativo.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'idoperativo': operativo.id, 'orden': operativo.orden, 'nombre': operativo.descripcion})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        if action == 'consultartactico':
            try:
                tactico = ObjetivoTactico.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'idoperativo': tactico.id, 'orden': tactico.orden, 'nombre': tactico.descripcion})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."}),

        if action == 'consultarestrategico':
            try:
                estrategico = ObjetivoEstrategico.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'idestrategico': estrategico.id, 'orden': estrategico.orden, 'nombre': estrategico.descripcion})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        if action == 'editacciones':
            try:
                acciones = AccionDocumento.objects.get(pk=request.POST['idaccionedit'])
                acciones.descripcion = request.POST['descripcion']
                acciones.orden = request.POST['ordenaccionedit']
                acciones.tipo = request.POST['tipoaccionedit']
                acciones.medioverificacion_id = request.POST['medioaccionedit']
                acciones.observacion = request.POST['id_obsaccionedit']
                acciones.enlace = request.POST['id_enlaceaccionedit']
                acciones.porcentaje = request.POST['porcentajeaccionedit']
                acciones.save(request)
                log(u'edito acciones de documento: %s' % acciones, request, "edit")
                return JsonResponse({"result": "ok", 'idacciones': acciones.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editindicadores':
            try:
                indicador = IndicadorPoa.objects.get(pk=request.POST['idindicadoredit'])
                indicador.descripcion = request.POST['descripcion']
                indicador.orden = request.POST['id_ordenindicadoredit']
                indicador.save(request)
                log(u'edito indicador : %s' % indicador, request, "edit")
                return JsonResponse({"result": "ok", 'idacciones': indicador.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editoperativos':
            try:
                operativos = ObjetivoOperativo.objects.get(pk=request.POST['idoperativoedit'])
                operativos.descripcion = request.POST['descripcion']
                operativos.orden = request.POST['id_ordenoperativoedit']
                operativos.save(request)
                log(u'edito objetivo operativos: %s' % operativos, request, "edit")
                return JsonResponse({"result": "ok", 'idoperativos': operativos.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edittacticos':
            try:
                tacticos = ObjetivoTactico.objects.get(pk=request.POST['idtacticoedit'])
                tacticos.descripcion = request.POST['descripcion']
                tacticos.orden = request.POST['id_ordentacticoedit']
                tacticos.save(request)
                log(u'edito objetivo tactico: %s' % tacticos, request, "edit")
                return JsonResponse({"result": "ok", 'idtacticos': tacticos.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editestrategicos':
            try:
                estrategicos = ObjetivoEstrategico.objects.get(pk=request.POST['idestrategicoedit'])
                estrategicos.descripcion = request.POST['descripcion']
                estrategicos.orden = request.POST['id_ordenestrategicoedit']
                estrategicos.save(request)
                log(u'edito objetivo estrategico : %s' % estrategicos, request, "edit")
                if estrategicos.carrera_id:
                    carrera = estrategicos.carrera.nombre
                else:
                    carrera = ''
                return JsonResponse({"result": "ok", 'idestrategicos': estrategicos.id, 'departamento': estrategicos.departamento.nombre, 'programa': estrategicos.programa.nombre, 'carrera': carrera})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addacciones':
            try:
                acciones = AccionDocumento(indicadorpoa_id=request.POST['idindicadoradd'],
                                           descripcion=request.POST['descripcion'],
                                           tipo=request.POST['tipoaccionadd'],
                                           medioverificacion_id=request.POST['medioaccionadd'],
                                           observacion=request.POST['id_obsaccionadd'],
                                           enlace=request.POST['id_enlaceaccionadd'],
                                           porcentaje=request.POST['porcentajeaccionadd'],
                                           orden=request.POST['id_ordenaccionadd'])
                acciones.save(request)
                log(u'agrego accion al documento: %s' % acciones, request, "add")
                return JsonResponse({"result": "ok", 'idacciones': acciones.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addindicador':
            try:
                indicador = IndicadorPoa(objetivooperativo_id=request.POST['idoperativoadd'],
                                         descripcion=request.POST['descripcion'],
                                         orden=request.POST['id_ordenindicadoradd'])
                indicador.save(request)
                log(u'añadio indicador: %s' % indicador, request, "add")
                return JsonResponse({"result": "ok", 'idindicador': indicador.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addoperativo':
            try:
                operativo = ObjetivoOperativo(objetivotactico_id=request.POST['idtacticoadd'],
                                              descripcion=request.POST['descripcion'],
                                              orden=request.POST['id_ordentacticoadd'])
                operativo.save(request)
                log(u'añadio objetivo operativo: %s' % operativo, request, "add")
                return JsonResponse({"result": "ok", 'idoperativo': operativo.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addtactico':
            try:
                tactico = ObjetivoTactico(objetivoestrategico_id=request.POST['idestrategicoadd'],
                                          descripcion=request.POST['descripcion'],
                                          orden=request.POST['id_ordenestrategicoadd'])
                tactico.save(request)
                log(u'añadio objetivo tactico: %s' % tactico, request, "add")
                return JsonResponse({"result": "ok", 'idtactico': tactico.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Objetivo Estratégico'
                    data['form'] = ObjetivoEstrategicoForm()
                    return render(request, 'poa_objestrategicos/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Objetivo Estratégico'
                    data['objetivo'] = objetivo = ObjetivoEstrategico.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(objetivo)
                    form = ObjetivoEstrategicoForm(initial=initial)
                    form.editar()
                    data['form'] = form
                    return render(request, 'poa_objestrategicos/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Objetivo Estratégico'
                    data['objetivo'] = ObjetivoEstrategico.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_objestrategicos/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'addestrategico':
                try:
                    data = {}
                    data['idperiodopoa'] = request.GET['idperiodopoa']
                    departamentosactivos = DistributivoPersona.objects.values_list('unidadorganica_id', flat=True).filter(estadopuesto_id=1, status=True)
                    data['listadepartamento'] = Departamento.objects.filter(pk__in=departamentosactivos,status=True).order_by('nombre')
                    data['listacarrera'] = Carrera.objects.filter(status=True).order_by('nombre')
                    data['listaprograma'] = ProgramaPoa.objects.filter(status=True)
                    template = get_template("poa_objestrategicos/addestrategico.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Objetivos Estratégicos'
            data['tipoaccion'] = TIPO_ACCION
            data['medioverificacion'] = MedioVerificacion.objects.filter(status=True)
            data['periodospoa'] = PeriodoPoa.objects.filter(pk__lt=8,status=True).order_by('-id')
            data['departamento'] = Departamento.objects.filter(status=True).order_by('nombre')
            data['carreras'] = Carrera.objects.filter(status=True).order_by('nombre')
            if 'idperiodopa' in request.GET:
                data['periodopoas'] = periodopoa = PeriodoPoa.objects.get(pk=request.GET['idperiodopa'])
            else:
                data['periodopoas'] = periodopoa = PeriodoPoa.objects.filter(status=True).order_by('-id')[0]
            if 'iddepartamentopoa' in request.GET:
                data['iddepartamentopoa'] = departamentopoa = Departamento.objects.get(pk=request.GET['iddepartamentopoa'])
            else:
                data['iddepartamentopoa'] = departamentopoa = Departamento.objects.filter(status=True).order_by('nombre')[0]
            objetivos = ObjetivoEstrategico.objects.filter(departamento_id=departamentopoa,periodopoa=periodopoa,status=True).order_by('-periodopoa__anio', 'departamento', 'programa', 'descripcion')
            data['objetivos'] = objetivos
            return render(request, "poa_objestrategicos/viewprueba.html", data)
