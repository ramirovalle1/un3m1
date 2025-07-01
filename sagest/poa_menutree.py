# -*- coding: UTF-8 -*-

import json
import calendar
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.messages.context_processors import messages
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext,Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import ObjetivoEstrategicoForm, DocumentosIndicadorPoaForm, AccionDocumentosDetallePoaForm
from sagest.funciones import encrypt_id, carreras_departamento
from sagest.models import ObjetivoEstrategico, PeriodoPoa, Departamento, AccionDocumento, TIPO_ACCION, \
    MedioVerificacion, IndicadorPoa, ObjetivoOperativo, ObjetivoTactico, ProgramaPoa, DistributivoPersona, MetaPoa, AccionDocumentoDetalle, SeccionDepartamento
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador,log



from sga.models import Carrera, MONTH_CHOICES, Materia


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    hoy = datetime.now()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'adicionarestrategico':
            try:
                objetivo = ObjetivoEstrategico(periodopoa_id=request.POST['id_periodopoa'],
                                                   departamento_id=request.POST['id_departamento'],
                                                   programa_id=request.POST['id_programa'],
                                                   descripcion=request.POST['id_descripcion'],
                                                   orden=request.POST['id_orden']
                                                   )
                objetivo.save(request)
                id_gestion, id_carrera = int(request.POST.get('id_gestion', 0)), int(request.POST.get('id_carrera', 0))
                if id_gestion != 0 and id_carrera == 0:
                    objetivo.gestion_id = id_gestion
                elif id_carrera != 0:
                    objetivo.carrera_id = id_carrera
                objetivo.save(request)
                log(u'Adiciono objetivo estrategico de poa: %s' % objetivo, request, "add")
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
                return JsonResponse({"result": "ok", 'idoperativo': operativo.id, 'orden': operativo.orden, 'nombre': operativo.descripcion, 'ponderacion': operativo.ponderacion, 'formula':operativo.formula})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        if action == 'consultaroperativometas':
            try:
                data = {}
                data['operativo'] = operativo = ObjetivoOperativo.objects.get(pk=request.POST['id'])
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['idperiodopoa'])
                if not operativo.metapoa_set.filter(status=True):
                    data['detalle'] = periodopoa.evaluacionperiodopoa_set.filter(status=True).order_by('id')
                else:
                    data['detallemetaspoa'] = operativo.metapoa_set.filter(status=True).order_by('evaluacionperiodo_id')
                template = get_template("poa_menutree/evaluacionperiodopoa.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'tipo': operativo.tipo, 'nombreindicador': operativo.descripcion, 'data': json_content})
                # return JsonResponse({"result": "ok", 'idoperativo': operativo.id, 'orden': operativo.orden, 'nombre': operativo.descripcion, 'tipo': operativo.tipo})
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
                # acciones.tipo = request.POST['tipoaccionedit']
                # acciones.observacion = request.POST['id_obsaccionedit']
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
                operativos.formula = request.POST['idformulaoperativoedit']
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
                                           # tipo=request.POST['tipoaccionadd'],
                                           # observacion=request.POST['id_obsaccionadd'],
                                           orden=request.POST['id_ordenaccionadd'])
                acciones.save(request)
                log(u'agrego medio de verificacion: %s' % acciones, request, "add")
                return JsonResponse({"result": "ok", 'idacciones': acciones.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addmetas':
            try:
                tipoindicador = request.POST['tipoindicador']
                idindicadormeta = ObjetivoOperativo.objects.get(pk=request.POST['idindicadormeta'])
                idindicadormeta.tipo = tipoindicador
                idindicadormeta.save(request)
                if not idindicadormeta.metapoa_set.filter(status=True):
                    for lista in request.POST['cadena'].split(','):
                        lis = lista.split('_')
                        codigo = lis[0]
                        valor = lis[1]
                        metaspoa = MetaPoa(objetivooperativo=idindicadormeta,
                                           numero=valor,
                                           evaluacionperiodo_id=codigo)
                        metaspoa.save(request)
                else:
                    for lista in request.POST['cadena'].split(','):
                        lis = lista.split('_')
                        codigo = lis[0]
                        valor = lis[1]
                        metaspoa = MetaPoa.objects.get(pk=codigo, status=True)
                        metaspoa.numero = valor
                        metaspoa.save(request)
                return JsonResponse({"result": "ok"})
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

        if action == 'addfechadocumento':
            try:
                documento = AccionDocumento.objects.get(pk=encrypt_id(request.POST['id']))
                url_redirect = request.POST['url_redirect']
                f = AccionDocumentosDetallePoaForm(request.POST, instancia=documento)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                detallesdocumento = AccionDocumentoDetalle(acciondocumento=documento,
                                                           inicio=f.cleaned_data['inicio'],
                                                           fin=f.cleaned_data['fin'],
                                                           mostrar=f.cleaned_data['mostrar'],
                                                           estado_accion=0)
                detallesdocumento.save(request)
                log(u'Adiciono detalles documento a poa: %s' % detallesdocumento, request, "add")
                return JsonResponse({"result": False, 'to':f'{url_redirect}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error {ex}"})

        if action == 'editfechadocumento':
            try:
                url_redirect = request.POST['url_redirect']
                detalledocumento = AccionDocumentoDetalle.objects.get(pk=encrypt_id(request.POST['id']))
                f = AccionDocumentosDetallePoaForm(request.POST, instancia=detalledocumento)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                detalledocumento.inicio=f.cleaned_data['inicio']
                detalledocumento.fin=f.cleaned_data['fin']
                detalledocumento.mostrar=f.cleaned_data['mostrar']
                detalledocumento.estado_accion=0
                detalledocumento.save(request)
                log(u'Edito detalles documento a poa: %s' % detalledocumento, request, "edit")
                return JsonResponse({"result": False, 'to':f'{url_redirect}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error {ex}"})

        if action == 'delfechadocumento':
            try:
                documento = AccionDocumentoDetalle.objects.get(pk=encrypt_id(request.POST['id']))
                documento.status = False
                documento.save(request)
                log(u'Elimino documento a poa: %s' % documento, request, "del")
                return JsonResponse({'error': False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error': True, 'mensaje': f'Error: {ex}'})

        elif action == 'moverobjetivos':
            try:
                objetivos = request.POST.getlist('objetivos')
                iddepartamento, idgestion, idcarrera = request.POST.get('departamento_mv', None),\
                                                       request.POST.get('gestion_mv', None), \
                                                       request.POST.get('carrera_mv', None)
                for ob in objetivos:
                    objetivo = ObjetivoEstrategico.objects.get(pk=int(ob))
                    objetivo.departamento_id = iddepartamento
                    objetivo.gestion_id = idgestion
                    objetivo.carrera_id = idcarrera
                    objetivo.save(request)
                    log(u'Edito objetivo estrategico: %s' % objetivo, request, "edit")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error {ex}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Objetivo Estratégico'
                    data['form'] = ObjetivoEstrategicoForm()
                    return render(request, 'poa_objestrategicos/add.html', data)
                except Exception as ex:
                    pass

            elif action == 'edit':
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

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Objetivo Estratégico'
                    data['objetivo'] = ObjetivoEstrategico.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_objestrategicos/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'addestrategico':
                try:
                    data = {}
                    data['idperiodopoa'] = request.GET['idperiodopoa']
                    data['iddepa'] = iddepa = int(request.GET['iddepa'])
                    data['idgestion'] = idgestion = int(request.GET.get('idgestion', 0))
                    data['idcarrera'] = idcarrera = int(request.GET.get('idcarrera', 0))
                    eDepartamento = Departamento.objects.get(id=iddepa)
                    titulo = str(eDepartamento)
                    if idgestion != 0 and idcarrera == 0:
                        eGestion = SeccionDepartamento.objects.get(id=idgestion)
                        titulo = str(eGestion)
                    if idcarrera != 0:
                        eCarrera = Carrera.objects.get(id=idcarrera)
                        titulo = str(eCarrera)
                    data['titulo'] = titulo
                    # departamentosactivos = DistributivoPersona.objects.values_list('unidadorganica_id', flat=True).filter(estadopuesto_id=1, status=True)
                    # data['listadepartamento'] = Departamento.objects.filter(pk__in=departamentosactivos, status=True).order_by('nombre')
                    data['listadepartamento'] = Departamento.objects.filter(integrantes__isnull=False, status=True).order_by('nombre').distinct()
                    data['listaprograma'] = ProgramaPoa.objects.filter(status=True)
                    template = get_template("poa_menutree/addestrategico.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addfechadocumento':
                try:
                    data['documento'] = documento = AccionDocumento.objects.get(pk=request.GET['id'])
                    anio = hoy.date().year
                    mes = hoy.date().month
                    last_day = calendar.monthrange(anio, mes)[1]
                    data['form'] = AccionDocumentosDetallePoaForm(initial={'inicio': hoy.date(),
                                                                               'fin': datetime(anio, mes, last_day).date(),
                                                                               'mostrar': True})
                    data['indicador'] = documento.indicadorpoa
                    data['id'] = documento.id
                    data['switchery'] = True
                    template = get_template('poa_menutree/modal/formacciondocumento.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editfechadocumento':
                try:
                    data['documento'] = documento = AccionDocumentoDetalle.objects.get(pk=encrypt_id(request.GET['id']))
                    data['form'] = AccionDocumentosDetallePoaForm(initial=model_to_dict(documento))
                    data['id'] = documento.id
                    data['switchery'] = True
                    template = get_template('poa_menutree/modal/formacciondocumento.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'moverobjetivos':
                try:
                    data = {}
                    idperiodo, iddepa, idgestion, idcarrera = request.GET['id'].split(',')
                    data['id'] = idperiodo= int(idperiodo) if idperiodo else 0
                    iddepa = int(iddepa) if iddepa else 0
                    idgestion = int(idgestion) if idgestion else 0
                    idcarrera = int(idcarrera) if idcarrera else 0
                    data['eDepartamento'] = eDepartamento = Departamento.objects.get(id=iddepa)

                    titulo = str(eDepartamento)
                    filtro = Q(periodopoa_id=idperiodo, status=True)
                    if idgestion != 0 and idcarrera == 0:
                        data['eGestion'] = eGestion = SeccionDepartamento.objects.get(id=idgestion)
                        titulo = str(eGestion)
                        filtro = filtro & Q(gestion=eGestion)
                    elif idcarrera != 0:
                        data['eCarrera'] = eCarrera = Carrera.objects.get(id=idcarrera)
                        titulo = str(eCarrera)
                        filtro = filtro & Q(carrera=eCarrera)
                    else:
                        filtro = filtro & Q(departamento=eDepartamento, carrera__isnull=True, gestion__isnull=True)
                    data['titulo'] = titulo
                    data['departamentos'] = Departamento.objects.filter(integrantes__isnull=False, status=True).distinct().order_by('nombre')
                    data['objetivos'] = ObjetivoEstrategico.objects.filter(filtro).order_by('orden')
                    template = get_template("poa_menutree/modal/formmoverobjetivos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error: %s" % ex})

            elif action == 'cargargestiones':
                try:
                    departamento = Departamento.objects.get(id=request.GET['id'])
                    resp = [{'value': qs.pk, 'text': f"{qs.descripcion}"}
                            for qs in departamento.gestiones()]
                    return JsonResponse({'result': True, 'data': resp})
                except Exception as ex:
                    pass

            elif action == 'cargarcarreras':
                try:
                    departamento = Departamento.objects.get(id=request.GET['id'])
                    carreras = carreras_departamento(departamento, periodo)
                    resp = [{'value': qs.pk, 'text': f"{qs}"}
                            for qs in carreras]
                    return JsonResponse({'result': True, 'data': resp})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'POA Administración'
                data['tipoaccion'] = TIPO_ACCION
                data['new'] = request.GET.get('new', False)
                data['idseleccion'] = request.GET.get('idseleccion', '')
                data['medioverificacion'] = MedioVerificacion.objects.filter(status=True)
                data['periodospoa'] = PeriodoPoa.objects.filter(pk__gte=8,status=True).order_by('-id')
                idperiodopoa = request.GET.get('idperiodopa', '')
                if idperiodopoa:
                    data['periodopoas'] = periodopoa = PeriodoPoa.objects.get(pk=idperiodopoa)
                else:
                    data['periodopoas'] = periodopoa = PeriodoPoa.objects.filter(status=True).order_by('-id').first()
                ids_departamentos = ObjetivoEstrategico.objects.values_list('departamento_id').filter(periodopoa=periodopoa, status=True)
                if not periodopoa.activo:
                    data['departamento'] = departamentoseleccionado = Departamento.objects.filter(pk__in=ids_departamentos, status=True).order_by('nombre')
                else:
                    data['departamento'] = departamentoseleccionado = Departamento.objects.filter((Q(integrantes__isnull=False) | Q(id__in=ids_departamentos)), status=True).distinct().order_by('nombre')
                iddepartamentopoa, gestion, carrera, filtro = request.GET.get('iddepartamentopoa', ''), \
                                                              int(request.GET.get('idgestion', '0')), \
                                                              int(request.GET.get('idcarrera', '0')), \
                                                              Q(periodopoa=periodopoa, status=True)
                if iddepartamentopoa:
                    data['iddepartamentopoa'] = departamentopoa = Departamento.objects.get(pk=iddepartamentopoa)
                else:
                    data['iddepartamentopoa'] = departamentopoa = departamentoseleccionado.filter(status=True)[0]

                titulo = str(departamentopoa)
                if gestion != 0 and carrera == 0:
                    data['idgestion'] = gestion
                    eGestion = SeccionDepartamento.objects.get(id=gestion)
                    titulo = str(eGestion)
                    filtro = filtro & Q(gestion_id=gestion)
                elif carrera != 0:
                    data['idcarrera'] = carrera
                    eCarrera = Carrera.objects.get(id=carrera)
                    titulo = str(eCarrera)
                    filtro = filtro & Q(carrera_id=carrera)
                else:
                    filtro = filtro & Q(departamento=departamentopoa, carrera__isnull=True, gestion__isnull=True)
                data['gestiones'] = departamentopoa.gestiones()
                # data['carreras'] = Carrera.objects.filter(coordinacion__id__in=departamentopoa.coordinaciones_ids(), status=True).distinct()
                data['carreras'] = carreras_departamento(departamentopoa, periodo)
                objetivos = ObjetivoEstrategico.objects.filter(filtro).order_by('orden')
                data['objetivos'] = objetivos
                data['meses'] = [x[1][:3] for x in MONTH_CHOICES]
                data['titulo'] = titulo
                return render(request, "poa_menutree/viewmenu.html", data)
            except Exception as ex:
                import sys
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                messages.error(request, f'Error: {ex}')