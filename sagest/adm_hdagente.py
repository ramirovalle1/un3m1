# -*- coding: latin-1 -*-
import json
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.aggregates import Count
from django.db.models.query_utils import Q
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from decorators import secure_module, last_access
from sagest.commonviews import secuencia_ordentrabajo
from sagest.forms import HdIncidenciaFrom, HdRequerimientoPiezaPartesForm, HdRequerimientosPiezaPartesForm, \
    SeleccionarActivoForm, DetalleOrdenForm, CerrarOrdenForm, HdMaterial_IncidenteForm, OrdenPedidoForm, DetalleOrdenPedidoForm
from sagest.models import HdSubCategoria, ActivoFijo, HdDetalle_SubCategoria, HdIncidente, Departamento, \
    HdDetalle_Grupo, HdDetalle_Incidente, HdEstado, HdEstado_Proceso, HdProceso, HdDirector, HdGrupo, HdBloque, \
    HdBloqueUbicacion, HdCategoria, HdPiezaPartes, HdRequerimientosPiezaPartes, HdSolicitudesPiezaPartes, HdCausas, \
    HdPrecioSolicitudesPiezaPartes, OrdenTrabajo, DetalleOrdenTrabajo, HdDetalle_Incidente_Ayudantes, \
    HdMaterial_Incidente, HdTipoIncidente, RequerimientoPiezaParteMultiple, OrdenPedido, DistributivoPersona, Producto, \
    DetalleOrdenPedido, HdMaterial_OrdenPedido_Incidente
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, generar_nombre, generar_codigo
from sga.models import Persona, Notificacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, add_tabla_reportlab, generar_pdf_reportlab, add_titulo_reportlab, add_graficos_barras_reportlab, add_graficos_circular_reporlab
from django.forms import model_to_dict

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    PREFIX = 'UNEMI'
    SUFFIX = 'OP'
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        # request.user.has_perm("sagest.puede_logistica_ingresar_incidente")
        if action == 'add':
            try:
                # if not request.user.has_perm('sagest.puede_adicionar_incidente'):
                    form = HdIncidenciaFrom(request.POST, request.FILES)
                    if not int(request.POST['persona']) > 0:
                        return JsonResponse({"result": "bad","mensaje": u"No ha seleccionado quien solicinta el incidente."})
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 4194304:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.pdf' or ext == '.jpg' or ext == '.png' or ext == '.jpeg' or ext == '.PDF' or ext == '.JPG' or ext == '.PNG' or ext == '.JPEG':
                                    newfile._name = generar_nombre("estadohelpdesk_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, Solo archivo con extención. pdf, jpg, png, jpeg."})
                    if form.is_valid():
                        if HdDirector.objects.filter(vigente=True).exists():
                            activo = None
                            if len(request.POST['activo'])>0:
                                if int(request.POST['activo'])>0:
                                    activo = int(request.POST['activo'])
                            incidente = HdIncidente(asunto=form.cleaned_data['asunto'],
                                                    persona_id=int(request.POST['persona']),
                                                    ubicacion_id=int(request.POST['ubicacion']),
                                                    descripcion=form.cleaned_data['descripcion'],
                                                    detallesubcategoria_id=request.POST['detallesubcategoria'] if request.POST['detallesubcategoria'] else None,
                                                    activo_id=activo,
                                                    fechareporte=datetime.now().date(),
                                                    horareporte=datetime.now().time(),
                                                    # horareporte=form.cleaned_data['horareporte'],
                                                    medioreporte_id=int(request.POST['medioreporte']),
                                                    estado_id=int(request.POST['estado']),
                                                    tipoincidente_id=int(request.POST['tipoincidente']),
                                                    director_id=HdDirector.objects.get(vigente=True,status=True).persona.id,
                                                    causa_id=int(request.POST['causa']) if request.POST['causa'] else None  if 'causa' in request.POST else None,
                                                    archivo=newfile
                                                    )
                            incidente.save(request)
                            # incidente.email_notificacion_tic(request.session['nombresistema'])
                            log(u'Adiciono nuevo Incidente: %s' % incidente, request, "add")
                            if request.POST['grupo']:
                                grupo = HdGrupo.objects.get(pk=int(request.POST['grupo']))
                                if grupo.hddetalle_grupo_set.filter(responsable=True).exists():
                                    detalle = HdDetalle_Incidente(incidente_id=incidente.id,
                                                                  grupo_id=int(request.POST['grupo']) if request.POST['grupo'] else None,
                                                                  agente_id=request.POST['agente'] if request.POST['agente'] else None,
                                                                  estadoasignacion=1,
                                                                  resolucion=form.cleaned_data['resolucion'] if 'resolucion' in request.POST else None,
                                                                  fecharesolucion=datetime.now().date(),
                                                                  horaresolucion=datetime.now().time(),
                                                                  estadoproceso_id=int(request.POST['estadobaja']) if 'estadobaja' in request.POST else None,
                                                                  responsable_id=grupo.hddetalle_grupo_set.get(responsable=True).persona.id,
                                                                  estado_id=int(request.POST['estado'])
                                                                  )
                                    detalle.save(request)
                                    if request.POST['agente']:
                                        detalle.email_notificacion_agente(request.session['nombresistema'])
                                    log(u'Adiciono nuevo Detalle: %s' % detalle, request, "add")
                                else:
                                    return JsonResponse({"result": "bad","mensaje": u"No ha definido un Responsable, registreló en configuración, Agentes."})
                            if incidente.revisionequiposincodigo and incidente.tipoincidente.id == 2:
                                incidente.email_notificacion_equipo_sin_codigo(request.session['nombresistema'])
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"No ha definido un Director,registrelo en configuración."})
                    else:
                        raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addmaterialincidente':
            try:
                materialincidente = HdMaterial_Incidente(incidente_id=request.POST['idincidente'],
                                                         material_id=request.POST['idmaterial'],
                                                         cantidad=request.POST['idcantidad'])
                materialincidente.save(request)
                log(u'Adiciono nuevo materialincidente: %s' % materialincidente, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'vermaterialesincidente':
            try:
                lista =[]
                incidente = HdIncidente.objects.get(pk=int(request.POST['idincidente']))
                data['materialesincidentes'] = incidente.hdmaterial_incidente_set.filter(status=True)
                template = get_template("adm_hdagente/consultalistamaterialincidente.html")
                json_content = template.render(data)
                return JsonResponse(
                    {"result": "ok", 'html': json_content, 'title': u'Seleccionar el periodo academico'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'delmaterialincidente':
            try:
                tipo = request.POST['tipo'] if 'tipo' in request.POST and request.POST['idmaterial'] else None
                id = request.POST['idmaterial'] if 'idmaterial' in request.POST and request.POST['idmaterial'] else 0
                if not tipo:
                    return JsonResponse({"result": "bad", "mensaje": "Error al consultar los datos."})
                material = None
                if tipo == 'op':
                    material = HdMaterial_OrdenPedido_Incidente.objects.get(pk=id)
                    if material:
                        material.delete()
                        log(u'Elimino material del incidente: %s' % material, request, "del")
                else:
                    material = HdMaterial_Incidente.objects.get(pk=id)
                    if material:
                        material.delete()
                        log(u'Elimino material del incidente: %s' % material, request, "del")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos: %s" % ex})

        if action == 'conmaterialesincidentes':
            try:
                nombre = None
                id = request.POST['idmater'] if 'idmater' in request.POST and request.POST['idmater'] else 0
                tipo = request.POST['tipo'] if 'tipo' in request.POST and request.POST['tipo'] else None
                if not tipo:
                    return JsonResponse({"result": "bad", "mensaje": "Error al consultar los datos."})
                if tipo == 'op':
                    material = HdMaterial_OrdenPedido_Incidente.objects.get(pk=id, status=True)
                    producto = material.material.producto.descripcion
                    documento = material.ordenpedido().codigodocumento
                    nombre = ("%s - %s" % (documento, producto))
                else:
                    material = HdMaterial_Incidente.objects.get(pk=id, status=True)
                    nombre = material.material.nombre
                return JsonResponse({"result": "ok", "nombre": nombre})
            except Exception as ex:
                #transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'resolverincidente':
            try:
                incidente = HdIncidente.objects.get(pk=int(request.POST['id']), status=True)
                form = HdIncidenciaFrom(request.POST)
                getactivo = None
                listaayudantes = None
                if form.is_valid():
                    revisionequipoexterno = form.cleaned_data['revisionequipoexterno'] if 'revisionequipoexterno' in request.POST else False
                    revisionequiposincodigo = form.cleaned_data['revisionequiposincodigo'] if 'revisionequiposincodigo' in request.POST else False
                    responsableactivofijo = None
                    if not (revisionequipoexterno or revisionequiposincodigo):
                        if not int(request.POST['activo']) > 0 and incidente.tipoincidente_id != 3:
                            return JsonResponse({"result": "bad", "mensaje": u"No ha seleccionado el activo."})
                        if len(request.POST['activo']) > 0:
                            if int(request.POST['activo']) > 0:
                                getactivo = ActivoFijo.objects.get(pk=int(request.POST['activo']))
                                if getactivo.responsable:
                                    responsableactivofijo = getactivo.responsable.id
                                else:
                                    responsableactivofijo = None
                    if incidente.tipoincidente:
                        agente = HdDetalle_Grupo.objects.get(persona=persona, estado=True, grupo__tipoincidente=incidente.tipoincidente)
                    else:
                        agente = HdDetalle_Grupo.objects.get(persona_id=persona.id, estado=True)
                    # activo = None
                    # if len(request.POST['activo']) > 0:
                    #     if int(request.POST['activo']) > 0:
                    #         getactivo = ActivoFijo.objects.get(pk=int(request.POST['activo']))
                    #         activo = getactivo.id
                    #         responsableactivofijo = getactivo.responsable.id
                    # if incidente.ultimo_registro():
                    #     listadetalle = incidente.ultimo_registro().hddetalle_incidente_ayudantes_set.values_list('agente_id', flat=True).filter(status=True)
                    #     listaayudantes = HdDetalle_Grupo.objects.filter(pk__in=listadetalle, status=True)
                    det = HdDetalle_Incidente(incidente=incidente,
                                              agente=agente,
                                              grupo=agente.grupo,
                                              resolucion=request.POST['resolucion'],
                                              fecharesolucion=datetime.now().date(),
                                              horaresolucion=datetime.now().time(),
                                              estadoasignacion=1,
                                              responsable_id=agente.grupo.hddetalle_grupo_set.get(responsable=True).persona.id,
                                              estadoproceso_id=request.POST['estadobaja'] if 'estadobaja' in request.POST else None,
                                              estado_id = int(request.POST['estado'])
                                              )
                    det.save(request)
                    listaayudantes = HdDetalle_Grupo.objects.filter(pk__in=form.cleaned_data['ayudantes'])
                    if listaayudantes:
                        for ayudante in listaayudantes:
                            detalleayudantes = HdDetalle_Incidente_Ayudantes(detallleincidente=det,
                                                                             agente=ayudante
                                                                             )
                            detalleayudantes.save(request)
                    log(u'Resolvio el incidente: %s' % det, request, "resol")
                    if not incidente.tipoincidente:
                        incidente.tipoincidente = agente.grupo.tipoincidente
                    incidente.estado_id = int(request.POST['estado'])
                    if 'subcategoria' in request.POST:
                        if request.POST['subcategoria']:
                            incidente.subcategoria_id = int(request.POST['subcategoria'])
                    if 'detallesubcategoria' in request.POST:
                        if request.POST['detallesubcategoria']:
                            incidente.detallesubcategoria_id = int(request.POST['detallesubcategoria'])
                    if 'causa' in request.POST:
                        incidente.causa_id = int(request.POST['causa']) if request.POST['causa'] else None
                    else:
                        incidente.causa_id = None
                    incidente.activo_id = getactivo.id if getactivo else getactivo
                    incidente.responsableactivofijo_id = responsableactivofijo
                    incidente.revisionequipoexterno = revisionequipoexterno
                    incidente.revisionequiposincodigo = revisionequiposincodigo
                    incidente.serie = form.cleaned_data['serie'] if 'serie' in request.POST else ''
                    incidente.save(request)
                    log(u'Resolvio el incidente: %s el agente: %s' % (incidente, agente), request, "resol")
                    if incidente.revisionequiposincodigo and incidente.tipoincidente.id == 2:
                        incidente.email_notificacion_equipo_sin_codigo(request.session['nombresistema'])
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'separarincidente':
            try:
                incidente = HdIncidente.objects.get(pk=request.POST['idinscripcioncohorteestado'])
                incidente.estado_id = 2
                incidente.save(request)
                agente = persona.hddetalle_grupo_set.filter(status=True, estado=True)[0]
                det = HdDetalle_Incidente(incidente=incidente,
                                          agente=agente,
                                          grupo=agente.grupo,
                                          fecharesolucion=datetime.now().date(),
                                          horaresolucion=datetime.now().time(),
                                          estadoasignacion=1,
                                          responsable_id=agente.grupo.hddetalle_grupo_set.get(responsable=True).persona.id,
                                          estadoproceso_id=request.POST['estadobaja'] if 'estadobaja' in request.POST else None,
                                          estado_id=2)
                det.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar."})

        if action == 'addrequerimientopiezaparte':
            try:
                f = HdRequerimientoPiezaPartesForm(request.POST)
                if f.is_valid():
                    piezaparte = request.POST.getlist('piezaparte[]')
                    caracteristica = request.POST.getlist('catacteristica[]')
                    # preciosolicitud = HdPrecioSolicitudesPiezaPartes.objects.filter(solicitudes=f.cleaned_data['listasolicitudes'],activo=True,status=True)[0].id
                    requerimiento = HdRequerimientosPiezaPartes(incidente_id=request.POST['id'],
                                                                # preciosolicitud_id = preciosolicitud,
                                                                # solicitudes=f.cleaned_data['listasolicitudes'],
                                                                tipoactivo=f.cleaned_data['tipoactivo'],
                                                                fecharesuelve=f.cleaned_data['fecha'])
                    requerimiento.save(request)
                    counter = 0
                    while counter < len(piezaparte):
                        detalle = RequerimientoPiezaParteMultiple(requerimiento=requerimiento,
                                                                  piezaparte_id=int(HdPiezaPartes.objects.get(descripcion=piezaparte[counter], status=True).id),
                                                                  descripcion=(caracteristica[counter]).upper())
                        detalle.save(request)
                        counter += 1
                    log(u'Adiciono requerimiento de pieza y parte: %s' % requerimiento, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'resolverrequerimiento':
            try:
                requerimiento = HdRequerimientosPiezaPartes.objects.get(pk=int(request.POST['id']))
                form = HdRequerimientosPiezaPartesForm(request.POST)
                if form.is_valid():
                    requerimiento.codigoresuelve = form.cleaned_data['codigoresuelve']
                    requerimiento.observacionresuelve = form.cleaned_data['observacionresuelve']
                    requerimiento.usuarioresuelve = persona.usuario
                    requerimiento.fecharesuelve = datetime.now()
                    requerimiento.save(request)
                    log(u'resolvio requerimiento pieza y partes: %s' % requerimiento, request, "editar")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detallerequerimiento':
            try:
                data['requerimiento'] = requerimiento = HdRequerimientosPiezaPartes.objects.get(pk=int(request.POST['id']))
                if requerimiento.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(usuario=requerimiento.usuario_creacion) if requerimiento.usuario_creacion.id > 1 else ""
                if requerimiento.usuarioresuelve:
                    data['usuarioresuelve'] = Persona.objects.get(usuario=requerimiento.usuarioresuelve) if requerimiento.usuarioresuelve.id > 1 else ""
                template = get_template("adm_hdagente/detallerequerimiento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action=='delrequerimientopiezaparte':
            try:
                requerimiento = HdRequerimientosPiezaPartes.objects.get(pk=int(request.POST['id']))
                log(u'Elimino requerimiento Pieza y Parte: %s' % requerimiento, request, "del")
                requerimiento.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente.."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'reasignaragente':
            try:
                incidente = HdIncidente.objects.get(pk=request.POST['id'])
                form = HdIncidenciaFrom(request.POST)
                if form.is_valid():
                    activo = None
                    revisionequipoexterno = form.cleaned_data['revisionequipoexterno'] if 'revisionequipoexterno' in request.POST else False
                    revisionequiposincodigo = form.cleaned_data['revisionequiposincodigo'] if 'revisionequiposincodigo' in request.POST else False
                    if not (revisionequipoexterno or revisionequiposincodigo):
                        if not int(request.POST['activo']) > 0:
                            return JsonResponse({"result": "bad", "mensaje": u"No ha seleccionado el activo."})
                        if len(request.POST['activo']) > 0:
                            if int(request.POST['activo']) > 0:
                                activo = int(request.POST['activo'])
                    if incidente.tipoincidente:
                        agente = HdDetalle_Grupo.objects.filter(persona_id=persona.id,grupo__tipoincidente=incidente.tipoincidente, status=True)[0]
                    else:
                        agente = HdDetalle_Grupo.objects.filter(persona_id=persona.id, status=True)[0]
                    if incidente.mi_detalle():
                        detalle = incidente.hddetalle_incidente_set.filter(status=True).order_by('-id')[0]
                        if not detalle.grupo:
                            detalle.grupo = agente.grupo
                        if not detalle.agente:
                            detalle.agente = agente
                        detalle.resolucion = form.cleaned_data['resolucion']
                        detalle.fecharesolucion = datetime.now().date()
                        detalle.horaresolucion = datetime.now().time()
                        detalle.estadoasignacion = 2
                        detalle.estado_id = 2
                        detalle.save(request)
                    else:
                        responsable = HdDetalle_Grupo.objects.filter(status=True, grupo=agente.grupo,responsable=True)[0]
                        detalle = HdDetalle_Incidente(incidente=incidente,
                                                      grupo=agente.grupo,
                                                      agente=agente,
                                                      resolucion=form.cleaned_data['resolucion'],
                                                      fecharesolucion = datetime.now().date(),
                                                      horaresolucion=datetime.now().time(),
                                                      estadoasignacion=2,
                                                      responsable=responsable.persona,
                                                      estado_id=2
                                                      )
                        detalle.save(request)
                    responsable = HdDetalle_Grupo.objects.filter(status=True, grupo_id=int(request.POST['grupo']), responsable=True)[0]
                    nuevodetalle = HdDetalle_Incidente(incidente=incidente,
                                                       grupo_id=int(request.POST['grupo']),
                                                       agente_id=int(request.POST['agente']),
                                                       estadoasignacion=1,
                                                       responsable=responsable.persona,
                                                       estado_id=2
                                                       )
                    nuevodetalle.save(request)
                    log(u'Reasignó el agente: %s al Agente: %s' % (detalle.agente, nuevodetalle.agente), request,"Reasig")
                    nuevodetalle.email_notificacion_agente_reasignado(request.session['nombresistema'], detalle)
                    incidente = HdIncidente.objects.get(id=detalle.incidente.id)
                    incidente.estado_id = 2
                    incidente.asunto = form.cleaned_data['asunto']
                    incidente.descripcion = form.cleaned_data['descripcion']
                    if request.POST['subcategoria']:
                        incidente.subcategoria_id = int(request.POST['subcategoria'])
                    if request.POST['detallesubcategoria']:
                        incidente.detallesubcategoria_id = int(request.POST['detallesubcategoria'])
                    incidente.revisionequipoexterno = revisionequipoexterno
                    incidente.revisionequiposincodigo = revisionequiposincodigo
                    incidente.serie = form.cleaned_data['serie'] if 'serie' in request.POST else ''
                    incidente.activo_id = activo
                    incidente.save(request)
                    log(u'Editó por reasignación la cabezera del incidente: %s' % incidente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'escalarincidente':
            try:
                incidente = HdIncidente.objects.get(pk=request.POST['id'])
                # if not int(request.POST['activo']) > 0:
                #     return JsonResponse({"result": "bad","mensaje": u"No ha seleccionado el activo."})
                form = HdIncidenciaFrom(request.POST)
                if form.is_valid():
                    getactivo = None
                    revisionequipoexterno = form.cleaned_data['revisionequipoexterno'] if 'revisionequipoexterno' in request.POST else False
                    revisionequiposincodigo = form.cleaned_data['revisionequiposincodigo'] if 'revisionequiposincodigo' in request.POST else False
                    responsableactivofijo = None
                    if not (revisionequipoexterno or revisionequiposincodigo):
                        if not int(request.POST['activo']) > 0 and form.cleaned_data['resolucion'] != 3:
                            return JsonResponse({"result": "bad", "mensaje": u"No ha seleccionado el activo."})
                        if len(request.POST['activo']) > 0:
                            if int(request.POST['activo']) > 0:
                                getactivo = ActivoFijo.objects.get(pk=int(request.POST['activo']))
                                if getactivo.responsable:
                                    responsableactivofijo = getactivo.responsable.id
                                else:
                                    responsableactivofijo = None
                    # if len(request.POST['activo']) > 0:
                    #     if int(request.POST['activo']) > 0:
                    #         activo = int(request.POST['activo'])
                    if incidente.tipoincidente:
                        agente = HdDetalle_Grupo.objects.filter(persona_id=persona.id, grupo__tipoincidente=incidente.tipoincidente, status=True)[0]
                    else:
                        agente = HdDetalle_Grupo.objects.filter(persona_id=persona.id, status=True)[0]
                    if incidente.mi_detalle():
                        detalle = incidente.hddetalle_incidente_set.filter(status=True).order_by('-id')[0]
                        if not detalle.estadoasignacion == 3:
                            if not detalle.grupo:
                                detalle.grupo = agente.grupo
                            if not detalle.agente:
                                detalle.agente = agente
                            detalle.resolucion = form.cleaned_data['resolucion']
                            detalle.fecharesolucion = datetime.now().date()
                            detalle.horaresolucion = datetime.now().time()
                            detalle.estadoasignacion = 3
                            detalle.estado_id = 2
                            detalle.save(request)
                        else:
                            responsable = HdDetalle_Grupo.objects.filter(status=True, grupo=agente.grupo, responsable=True)[0]
                            detalle = HdDetalle_Incidente(incidente=incidente,
                                                          grupo=agente.grupo,
                                                          agente=agente,
                                                          resolucion=form.cleaned_data['resolucion'],
                                                          fecharesolucion=datetime.now().date(),
                                                          horaresolucion=datetime.now().time(),
                                                          estadoasignacion=3,
                                                          responsable=responsable.persona,
                                                          estado_id=2
                                                          )
                            detalle.save(request)
                    else:
                        responsable = HdDetalle_Grupo.objects.filter(status=True, grupo=agente.grupo, responsable=True)[0]
                        detalle = HdDetalle_Incidente(incidente=incidente,
                                                      grupo=agente.grupo,
                                                      agente=agente,
                                                      resolucion=form.cleaned_data['resolucion'],
                                                      fecharesolucion=datetime.now().date(),
                                                      horaresolucion=datetime.now().time(),
                                                      estadoasignacion=3,
                                                      responsable=responsable.persona,
                                                      estado_id=2
                                                      )
                        detalle.save(request)
                    # nuevodetalle.email_notificacion_escalar(request.session['nombresistema'], detalle)
                    if 'subcategoria' in request.POST:
                        if request.POST['subcategoria']:
                            incidente.subcategoria_id = int(request.POST['subcategoria'])
                    if 'detallesubcategoria' in request.POST:
                        if request.POST['detallesubcategoria']:
                            incidente.detallesubcategoria_id = int(request.POST['detallesubcategoria'])
                    incidente.tipoincidente_id = int(request.POST['tipoincidente'])
                    incidente.estado_id = 2
                    incidente.activo_id = getactivo.id if getactivo else getactivo
                    incidente.responsableactivofijo_id = responsableactivofijo
                    incidente.revisionequipoexterno = revisionequipoexterno
                    incidente.revisionequiposincodigo = revisionequiposincodigo
                    incidente.serie = form.cleaned_data['serie'] if 'serie' in request.POST else ''
                    incidente.save(request)
                    log(u'El agente: %s escalo el incidente: %s al grupo: %s' % (detalle.agente, incidente, incidente.tipoincidente), request, "Esc")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'informeincidente':
            try:
                grupo = HdDetalle_Grupo.objects.get(estado=True,persona=persona).grupo
                fechainicio = datetime.strptime(request.POST['ini'], "%d-%m-%Y").date()
                fechafin = datetime.strptime(request.POST['fin'], "%d-%m-%Y").date()
                if fechafin >= datetime.now().date():
                    fechafin = datetime.now().date() + timedelta(days=-1)
                incidentes = HdIncidente.objects.filter(fechareporte__range=(fechainicio, fechafin), estado=3, subcategoria__id__isnull=False, hddetalle_incidente__agente__grupo=grupo).distinct()
                agentesatendieron = incidentes.values_list('hddetalle_incidente__agente__persona__apellido1', 'hddetalle_incidente__agente__persona__apellido2', 'hddetalle_incidente__agente__persona__nombres').annotate(contado=Count('hddetalle_incidente__agente__id')).order_by('hddetalle_incidente__agente__persona__apellido1', 'hddetalle_incidente__agente__persona__apellido2', 'hddetalle_incidente__agente__persona__nombres','contado')
                categoriasatendida = incidentes.values_list('detallesubcategoria__subcategoria__categoria__nombre').annotate(contado=Count('detallesubcategoria__subcategoria__categoria__id')).order_by('detallesubcategoria__subcategoria__categoria__nombre', 'contado')
                subcategoriasatendidas = incidentes.values_list('detallesubcategoria__subcategoria__id', 'detallesubcategoria__subcategoria__nombre').annotate(contado=Count('detallesubcategoria__subcategoria__id')).order_by('detallesubcategoria__subcategoria__nombre', 'contado')
                add_titulo_reportlab(descripcion = "INFORME DE INCIDENTES", tamano = 16,  espacios = 19)
                add_titulo_reportlab(descripcion = "GRUPO DE " + grupo.nombre + " " + fechainicio.strftime("%d-%m-%Y") + " al " + fechafin.strftime("%d-%m-%Y"), tamano = 14, espacios = 19)
                add_tabla_reportlab(encabezado = [('Nº','INCIDENTES RESUELTOS POR AGENTE','VALOR')],
                                    detalles = [(contador + 1, u'%s %s %s'% (agente[0], agente[1], agente[2]), agente[3]) for contador, agente in  enumerate(agentesatendieron)],
                                    anchocol = [50, 300, 100],
                                    cabecera_left_center = [True, False, True],
                                    detalle_left_center = [True, False, True])
                add_graficos_circular_reporlab(datavalor = [agente[3] for agente in agentesatendieron],
                                               datanombres = [u'%s %s'% (agente[0], agente[1]) for agente in agentesatendieron],
                                               anchografico = 150, altografico = 150,
                                               posiciongrafico_x = 120,  posiciongrafico_y = 20,
                                               titulo = 'INCIDENTES RESUELTOS POR AGENTE', tamanotitulo = 10,
                                               ubicaciontitulo_x = 90, ubicaciontitulo_y = 12)
                add_tabla_reportlab(encabezado = [('Nº', 'CATEGORIAS ATENDIDAS', 'VALOR')],
                                    detalles = [(contador + 1, categoria[0], categoria[1]) for contador, categoria in enumerate(categoriasatendida)],
                                    anchocol = [50, 300, 100],
                                    cabecera_left_center = [True, False, True],
                                    detalle_left_center = [True, False, True])
                add_graficos_barras_reportlab(datavalor = [[categoria[1] for categoria in categoriasatendida]],
                                              datanombres = [categoria[0] if categoria[0] else  'SIN CATEGORIA' for categoria in categoriasatendida],
                                              anchografico = 300, altografico = 125, tamanoletra = 6,
                                              posiciongrafico_x = 100, posiciongrafico_y = 30,
                                              titulo = 'CATEGORIAS ATENDIDAS', tamanotitulo = 10,
                                              ubicaciontitulo_x = 140, ubicaciontitulo_y = 12, mostrarleyenda=False)
                add_tabla_reportlab(encabezado=[('Nº', 'SUBCATEGORIAS SOFTWARE Y HARDWARE', 'VALOR')],
                                    detalles=[(contador + 1 , subcategoria[1], subcategoria[2]) for contador, subcategoria in enumerate(subcategoriasatendidas)],
                                    anchocol=[50, 300, 100], cabecera_left_center=[True, False, True],
                                    detalle_left_center=[True, False, True])
                add_graficos_barras_reportlab(datavalor=[[subcategoria[2] for subcategoria in subcategoriasatendidas]],
                                              datanombres=[subcategoria[1] if subcategoria[1] else  'SIN SUBCATEGORIA' for subcategoria in subcategoriasatendidas],
                                              anchografico=300, altografico=125, tamanoletra=6,
                                              posiciongrafico_x=100, posiciongrafico_y=30,
                                              titulo='SUBCATEGORIAS SOFTWARE Y HARDWARE', tamanotitulo=10,
                                              ubicaciontitulo_x=140, ubicaciontitulo_y=12,  posicionleyenda_x = 430, mostrarleyenda=False)
                for subcategoria in subcategoriasatendidas:
                    detalles_subcategorias = incidentes.values_list('detallesubcategoria__nombre').filter(detallesubcategoria__isnull=False).annotate(contado=Count('detallesubcategoria__id')).order_by('detallesubcategoria__nombre', 'contado')
                    add_tabla_reportlab(encabezado=[('Nº', 'SUBCATEGORIAS '+subcategoria[1] if subcategoria[1] else  'SIN SUBCATEGORIA', 'VALOR')],
                                        detalles=[(contador + 1,detalle_subcategoria[0], detalle_subcategoria[1].__str__()) for contador, detalle_subcategoria in enumerate(detalles_subcategorias)],
                                        anchocol=[50, 300, 100], cabecera_left_center=[True, False, True],
                                        detalle_left_center=[True, False, True])
                    add_graficos_barras_reportlab(datavalor=[[detalle_subcategoria[1] for detalle_subcategoria in detalles_subcategorias]],
                                                  datanombres=[detalle_subcategoria[0] if detalle_subcategoria[0] else  'SIN DETALLE DE SUBCATEGORIA' for detalle_subcategoria in detalles_subcategorias],
                                                  anchografico=300, altografico=125, tamanoletra=6,
                                                  posiciongrafico_x=100, posiciongrafico_y=30,
                                                  titulo=('SUBCATEGORIAS '+subcategoria[1] if subcategoria[1] else  'SIN SUBCATEGORIA'), tamanotitulo=10,
                                                  ubicaciontitulo_x=140, ubicaciontitulo_y=12, posicionleyenda_x=430, mostrarleyenda=False)
                return generar_pdf_reportlab()
            except Exception as ex:
                pass

        if action == 'selectgrupos':
            try:
                if 'id' in request.POST:
                    lista = []
                    listacategoria = []
                    listaestados = []
                    mi_tipo = False
                    grupos = HdGrupo.objects.filter(tipoincidente_id=int(request.POST['id']),status=True)
                    categorias = HdCategoria.objects.filter(status=True)
                    for grupo in grupos:
                        lista.append([grupo.id, grupo.nombre])
                    if HdDetalle_Grupo.objects.filter(persona=persona, grupo__tipoincidente_id=int(request.POST['id'])).exists():
                        if int(request.POST['id']) == HdDetalle_Grupo.objects.filter(persona=persona, grupo__tipoincidente_id=int(request.POST['id']))[0].grupo.tipoincidente.id:
                            mi_tipo = True
                    estados = HdEstado.objects.filter(pk=1)
                    if mi_tipo:
                        estados = HdEstado.objects.filter(pk__in=[1,2,3])
                    for cat in categorias:
                        listacategoria.append([cat.id, cat.nombre])
                    for s in estados:
                        listaestados.append([s.id, s.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista, 'mi_tipo':mi_tipo, "listacategoria":listacategoria, "listaestados":listaestados})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'listadopartes':
            try:
                parte = HdPiezaPartes.objects.values_list('id','descripcion').filter(hdsolicitudespiezapartes__isnull=False).distinct()
                if parte.count() > 0:
                    partes = []
                    for r in parte:
                        partes.append({"id": r[0], "valor": r[1]})
                    return JsonResponse({"result": "ok", "data": partes})
                return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        if action == 'listadopartesdetalle':
            try:
                solicitud = HdSolicitudesPiezaPartes.objects.filter(hdpreciosolicitudespiezapartes__activo=True,hdpreciosolicitudespiezapartes__status=True,status=True,piezaparte_id=int(request.POST['idpiezaparte']))
                if solicitud.count() > 0:
                    solicitudes = []
                    for r in solicitud:
                        detalle = r.tipo + ' - ' + r.capacidad + ' - ' + r.velocidad + ' - PRECIO ACTIVO: ' + str(r.precioactivo())
                        solicitudes.append({"id": r.id, "valor": detalle})
                    return JsonResponse({"result": "ok", "data": solicitudes})
                return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        if action == 'selectagentes':
            try:
                if 'id' in request.POST:
                    lista = []
                    agentes = HdDetalle_Grupo.objects.filter(grupo_id=int(request.POST['id']), status=True)
                    tiene_responsable = False
                    for agente in agentes:
                        lista.append([agente.id, agente.persona.nombres + ' ' + agente.persona.apellido1 + ' ' + agente.persona.apellido2])
                        if agente.responsable:
                            tiene_responsable = True
                    data = {"results": "ok", 'lista': lista, 'tiene_responsable': tiene_responsable}
                    return JsonResponse(data)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'selectestadoshicidente':
            try:
                lista = []
                estados = HdEstado.objects.filter(status=True).exclude(id__in=[1,4])
                for estado in estados:
                    lista.append([estado.id, estado.nombre])
                data = {"results": "ok", 'lista': lista}
                return JsonResponse(data)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'selectcategoria':
            try:
                if 'id' in request.POST:
                    lista = []
                    subcatecorias = HdSubCategoria.objects.filter(categoria_id=int(request.POST['id']),status=True)
                    for subcat in subcatecorias:
                        lista.append([subcat.id, subcat.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'selectdetalle':
            try:
                if 'id' in request.POST:
                    lista = []
                    detalles = HdDetalle_SubCategoria.objects.filter(subcategoria_id=int(request.POST['id']), status=True)
                    for detalle in detalles:
                        lista.append([detalle.id, detalle.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'valiprioridad':
            try:
                if 'id' in request.POST:
                    detalle = HdDetalle_SubCategoria.objects.get(pk=int(request.POST['id']), status=True)
                    tiene_prioridad = False
                    pri = ''
                    if detalle.prioridad:
                        tiene_prioridad = True
                        pri = detalle.prioridad.prioridad.nombre
                    data = {"result": "ok", 'tiene_prioridad': tiene_prioridad, 'pri': pri}
                    return JsonResponse(data)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'selectubicacion':
            try:
                if 'id' in request.POST:
                    lista = []
                    ubicaciones = HdBloqueUbicacion.objects.filter(bloque_id=int(request.POST['id']), status=True)
                    for ubi in ubicaciones:
                        lista.append([ubi.id, ubi.ubicacion.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'datosactivo':
            try:
                if 'id' in request.POST:
                    activo = ActivoFijo.objects.get(pk=int(request.POST['id']), status=True)
                    fecha = datetime.strftime(activo.fechaingreso, '%Y-%m-%d')
                    vfecha = fecha.split('-')
                    vfecha[0] = str(int(vfecha[0]) + activo.vidautil)
                    fechacaducidad = activo.fecha_caducidad()
                    return JsonResponse({"result": "ok", 'fechaingreso': str(activo.fechaingreso), 'vidautil': str(activo.vidautil),'tiempo': fechacaducidad})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'selectestado':
            try:
                if 'id' in request.POST:
                    lista = []
                    estado = HdEstado.objects.get(pk=int(request.POST['id']), status=True)
                    esta_resuelto = False
                    if estado.id == 3:
                        esta_resuelto = True
                        for lis in HdProceso.objects.filter(pk=2, status=True):
                            lista.append([lis.id, lis.nombre])
                    return JsonResponse({"result": "ok", 'esta_resuelto': esta_resuelto, "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'selectestadoproceso':
            try:
                if 'id' in request.POST:
                    lista = []
                    proceso = HdProceso.objects.get(pk=int(request.POST['id']), status=True)
                    for lis in proceso.hdestado_proceso_set.all():
                        lista.append([lis.id, lis.nombre])
                    return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'selectdetalleestpro':
            try:
                if 'id' in request.POST:
                    estado = HdEstado_Proceso.objects.get(pk=int(request.POST['id']), status=True)
                    return JsonResponse({"results": "ok", "detalle": estado.detalle if estado.detalle else ''})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'modaldetalle':
            try:
                if 'id' in request.POST:
                    data['incidente'] = incidente = HdIncidente.objects.get(pk=int(request.POST['id']), status=True)
                    if incidente.usuario_creacion:
                        data['personacreacion'] = Persona.objects.get(usuario=incidente.usuario_creacion) if incidente.usuario_creacion.id > 1 else ""
                    if incidente.activo:
                        fecha = datetime.strftime(incidente.activo.fechaingreso, '%Y-%m-%d')
                        vfecha = fecha.split('-')
                        vfecha[0] = str(int(vfecha[0]) + incidente.activo.vidautil)
                        data['fechacaducidad'] = str(vfecha[0] + '/' + vfecha[1] + '/' + vfecha[2])
                    template = get_template("adm_hdagente/modaldetalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'seleccionaractivo':
            try:
                if 'id' in request.POST and 'ida' in request.POST:
                    incidente = HdIncidente.objects.get(pk=int(request.POST['id']))
                    activo = ActivoFijo.objects.get(pk=int(request.POST['ida']))
                    incidente.activo = activo
                    incidente.revisionequiposincodigo = False
                    incidente.save(request)
                    log(u'Cambio el código del activo sin coóigo de barra o cogigo interno al incidente: %s' % incidente, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al buacar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'generarot':
            mensaje = "Problemas al generar Orden de trabajo."
            try:
                incidente = HdIncidente.objects.get(id=request.POST['id'])
                if incidente.tipoincidente_id == 3 and incidente.ordentrabajo == None:
                    secuencia = secuencia_ordentrabajo(request, datetime.now().year)
                    secuencia.secuenciaincidente += 1
                    secuencia.save(request)
                    ordentrabajo = OrdenTrabajo(codigoorden="0000"+str(secuencia.secuenciaincidente) + str("-"+str(datetime.now().year)))
                    ordentrabajo.save()
                    incidente.ordentrabajo = ordentrabajo
                    incidente.save()
                return conviert_html_to_pdf('adm_hdincidente/ordentrabajo.html',
                                            {'pagesize': 'A4',
                                             'incidente': incidente,'hoy':datetime.now().date()
                                             })
            except Exception as ex:
                return HttpResponseRedirect("/adm_hdincidente?info=%s" % mensaje)

        if action == 'imprimirincidente':
            mensaje = "Problemas al Imprimir incidente."
            try:
                listaayudantes = None
                incidente = HdIncidente.objects.get(id=request.POST['id'])
                if incidente.ultimo_registro():
                    listadetalle = incidente.ultimo_registro().hddetalle_incidente_ayudantes_set.values_list('agente_id', flat=True).filter(status=True)
                    listaayudantes = HdDetalle_Grupo.objects.filter(pk__in=listadetalle, status=True)
                materialesincidentes = incidente.hdmaterial_incidente_set.filter(status=True)
                return conviert_html_to_pdf('adm_hdincidente/pdf_incidente.html',
                                            {'pagesize': 'A4',
                                             'incidente': incidente,'listaayudantes': listaayudantes,'materialesincidentes': materialesincidentes,'hoy':datetime.now().date()
                                             })
            except Exception as ex:
                return HttpResponseRedirect("/adm_hdincidente?info=%s" % mensaje)

        if action == 'cerrarorden':
            try:
                form = CerrarOrdenForm(request.POST)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.jpg' or ext == '.png' or ext == '.jpeg' or ext == '.PDF' or ext == '.JPG' or ext == '.PNG' or ext == '.JPEG':
                                newfile._name = generar_nombre("ordentrabajo_", newfile._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf, jpg, png, jpeg."})
                if form.is_valid():
                    ordentrabajo = OrdenTrabajo.objects.get(pk=int(request.POST['id']))
                    if ordentrabajo.estado != form.cleaned_data['estado']:
                        ordentrabajo.estado = form.cleaned_data['estado']
                    ordentrabajo.informe=form.cleaned_data['informe']
                    ordentrabajo.archivo=newfile
                    ordentrabajo.save(request)
                    datos = json.loads(request.POST['lista_items1'])
                    listaeditar = []
                    if not datos:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar personas."})
                    for d in datos:
                        ne = d['ne']
                        if ne[:1] == 'e':
                            listaeditar.append(int(ne[1:ne.__len__()]))
                    ordentrabajo.detalleordentrabajo_set.all().exclude(pk__in=listaeditar).delete()
                    for d in datos:
                        ne = d['ne']
                        repuesto = str(d['repuesto'])
                        cantidad = str(d['cantidad'])
                        if ne[:1] == 'n':
                            detalle = DetalleOrdenTrabajo(orden=ordentrabajo,
                                                   repuesto=repuesto,
                                                   cantidad=cantidad)
                        else:
                            detalle=DetalleOrdenTrabajo.objects.get(pk=int(ne[1:ne.__len__()]))
                            detalle.repuesto=repuesto
                            detalle.cantidad=cantidad
                        detalle.save(request)
                    if form.cleaned_data['estado'] == 2:
                        incidente = HdIncidente.objects.filter(status=True, ordentrabajo=ordentrabajo)[0]
                        if incidente.tipoincidente:
                            agente = HdDetalle_Grupo.objects.get(persona=persona, estado=True, grupo__tipoincidente=incidente.tipoincidente)
                        else:
                            agente = HdDetalle_Grupo.objects.get(persona_id=persona.id, estado=True)
                        det = HdDetalle_Incidente(incidente=incidente,
                                                  agente=agente,
                                                  grupo=agente.grupo,
                                                  resolucion=form.cleaned_data['informe'],
                                                  fecharesolucion=datetime.now().date(),
                                                  horaresolucion=datetime.now().time(),
                                                  estadoasignacion=1,
                                                  responsable_id=agente.grupo.hddetalle_grupo_set.get(responsable=True).persona.id,
                                                  estado_id = 3
                                                  )
                        det.save(request)
                        log(u'Resolvio el incidente: %s' % det, request, "edit")
                        if not incidente.tipoincidente:
                            incidente.tipoincidente = agente.grupo.tipoincidente
                        incidente.estado_id = 3
                        incidente.save(request)
                    log(u'Cerro Orden de trabajo: %s' % ordentrabajo, request, "edit")
                    return JsonResponse({"result": "ok", "mensaje": u"Se cerro correcto."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'SearchProduct':
            try:
                if not 'q' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})
                q = request.POST['q']
                productos = Producto.objects.filter(Q(cuenta__cuenta__icontains=q) |
                                                    Q(codigo__icontains=q) |
                                                    Q(descripcion__icontains=q) |
                                                    Q(alias__icontains=q), status=True).distinct()[:20]
                results = []
                for producto in productos:
                    results.append({"id": producto.id,
                                    "alias": producto.flexbox_alias_orden_pedido(),
                                    "name": producto.flexbox_repr_orden_pedido()})
                return JsonResponse({"result": "ok", "results": results})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'SaveAddOrdenPedido':
            try:
                f = OrdenPedidoForm(request.POST)
                incidete = HdIncidente.objects.get(id=int(request.POST['incidente_id']))
                distributivo = DistributivoPersona.objects.filter(status=True, persona=persona)[0]
                descripcion = ("Solicitud de pedidos de materiales para la orden de pedido Nro. %s solicitado por %s" % (incidete.ordentrabajo.codigoorden, incidete.persona))
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    if not datos:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Error al guardar los datos, no registra detalles de productos"})

                    numerodocumento = 1
                    try:
                        numerodocumento = OrdenPedido.objects.all().order_by("-id")[0].numerodocumento
                        numerodocumento = int(numerodocumento) + 1
                    except:
                        pass

                    ordenPedido = OrdenPedido(departamento=distributivo.unidadorganica,
                                              responsable=persona,
                                              denominacionpuesto=distributivo.denominacionpuesto.descripcion,
                                              director=distributivo.unidadorganica.responsable,
                                              directordenominacionpuesto=DistributivoPersona.objects.filter(status=True,
                                                                                                            persona=distributivo.unidadorganica.responsable,
                                                                                                            unidadorganica=distributivo.unidadorganica)[0].denominacionpuesto.descripcion,
                                              numerodocumento=numerodocumento,
                                              codigodocumento=generar_codigo(numerodocumento, PREFIX, SUFFIX),
                                              fechaoperacion=datetime.now(),
                                              descripcion=descripcion,
                                              observaciones=f.cleaned_data['observaciones'])
                    ordenPedido.save(request)
                    for elemento in datos:
                        producto = Producto.objects.get(pk=int(elemento['id']))
                        if not producto:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"El producto %s no exite." % int(elemento['id'])})

                        cantidad = Decimal(elemento['cantidad']).quantize(Decimal('.0001'))
                        costo = Decimal(elemento['costo']).quantize(Decimal('.000000000000001'))
                        existencia = Decimal(elemento['stock']).quantize(Decimal('.0001'))
                        valor = costo * cantidad

                        detalleOrdenPedido = DetalleOrdenPedido(producto=producto,
                                                                cantidad=cantidad,
                                                                costo=costo,
                                                                valor=valor,
                                                                existencia=existencia
                                                                )
                        detalleOrdenPedido.save(request)
                        ordenPedido.productos.add(detalleOrdenPedido)
                    ordenPedido.save(request)
                    log(u'Adiciono orden de pedido: %s' % ordenPedido, request, "add")
                    #incidete.ordenpedido = ordenPedido
                    incidete.ordenpedidos.add(ordenPedido)
                    incidete.save(request)
                    log(u'Edito y adiciono orden de pedido: %s' % incidete, request, "edit")
                    url = ("%s?id=%s" % (request.path, ordenPedido.id))
                    notificacion = Notificacion(titulo='Nueva Orden de Pedido Nro. %s' % ordenPedido.codigodocumento,
                                                cuerpo='Tiene una una orden de pedido Nro. %s, con estado Solicitado' % ordenPedido.codigodocumento,
                                                destinatario=ordenPedido.director,
                                                url=url,
                                                content_type=ContentType.objects.get_for_model(ordenPedido),
                                                object_id=ordenPedido.pk,
                                                prioridad=2,
                                                fecha_hora_visible=datetime.now() + timedelta(days=30),
                                                app_label='sagest'
                                                )
                    notificacion.save(request)
                    log(u'Adiciono una notificación de orden de pedido: %s' % ordenPedido, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'LoadDetailOrdenPedido':
            try:
                data['orden'] = orden = OrdenPedido.objects.get(pk=request.POST['id'])
                data['detalles'] = orden.productos.all()
                template = get_template("adm_hdagente/detallesordenpedido.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'numero': orden.codigodocumento})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'LoadDetailOrdenPedidoMaterial':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] else 0
                hdincidente = HdIncidente.objects.get(pk=id)
                if not hdincidente:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos"})
                data['incidente'] = hdincidente
                ordenpedidos = hdincidente.ordenpedidos.filter(anulado=False, estado=2)
                data['ordenpedidos'] = ordenpedidos
                #ids_ordenpedido = ordenpedidos.values_list("id")
                #data['detalles'] = ordenpedidos.productos.filter(pk__in=[ids_ordenpedido])
                template = get_template("adm_hdagente/detallesmaterialesordenpedido.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex})

        if action == 'AddMaterialOrdenPedido':
            try:
                idi = int(request.POST['idi']) if 'idi' in request.POST and request.POST['idi'] else 0
                idd = int(request.POST['idd']) if 'idd' in request.POST and request.POST['idd'] else 0
                cantidad = request.POST['cantidad'] if 'cantidad' in request.POST and request.POST['cantidad'] else 0
                incidente = HdIncidente.objects.get(pk=idi)
                detalle = DetalleOrdenPedido.objects.get(pk=idd)
                if not incidente or not detalle:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos"})
                if not cantidad:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, cantidad debe mayor a cero"})

                material = HdMaterial_OrdenPedido_Incidente(incidente=incidente,
                                                 material=detalle,
                                                 cantidad=cantidad)
                material.save(request)
                log(u'Adiciono material: %s' % material, request, "add")
                data["materialesincidentes"] = HdMaterial_OrdenPedido_Incidente.objects.filter(incidente=incidente)
                template = get_template("adm_hdagente/loadlistmaterialincidente.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "mensaje": u"Se agrego material, correctamente", "aData": json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'LoadMaterialOrdenPedido':
            try:
                idi = int(request.POST['idi']) if 'idi' in request.POST and request.POST['idi'] else 0
                incidente = HdIncidente.objects.get(pk=idi)
                if not incidente:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos"})
                data["materialesincidentes"] = HdMaterial_OrdenPedido_Incidente.objects.filter(incidente=incidente, status=True)
                template = get_template("adm_hdagente/loadlistmaterialincidente.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "aData": json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud incorrecta"})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'buscaradmin':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s) == 1:
                        per = Persona.objects.filter((Q(profesor__isnull=False)), Q(nombres__icontains=q)|Q(apellido1__icontains=q)|Q(apellido2__icontains=q)|Q(cedula__contains=q), status= True).distinct()[:15]
                    elif len(s) == 2:
                        per = Persona.objects.filter((Q(profesor__isnull=False)), (Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1]))| (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1]))|(Q(nombres__icontains=s[0])&Q(apellido1__contains=s[1]))).filter(status=True,).distinct()[:15]
                    else:
                        per = Persona.objects.filter((Q(profesor__isnull=False)), (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True, ).distinct()[:15]
                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_repr()} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'buscardepartamento':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        depar = Departamento.objects.filter(nombre__icontains=s[0],codigo__icontains=s[0],alias__icontains=s[0], status= True).distinct()[:20]
                    else:
                        depar = Departamento.objects.filter((Q(nombre__icontains=s[0]) | Q(codigo__icontains=s[0]) | Q(alias__icontains=s[0]))).filter(status=True).distinct()[:20]
                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_repr()} for x in depar]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'buscaractivo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    tipo = int(request.GET['idt'])
                    if s.__len__() == 1:
                        # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                        activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True).distinct()[:20]
                    else:
                        activo = ActivoFijo.objects.filter((Q(codigogobierno__icontains=s[0])& Q(codigointerno__icontains=s[1]))|
                                                           (Q(codigogobierno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                                                           (Q(codigogobierno__icontains=s[0]) & Q(descripcion__icontains=s[1])) |
                                                           (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1])) |
                                                           (Q(codigointerno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                                                           # (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                                                           (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True).distinct()[:20]
                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_reprhd()} for x in activo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Incidente'
                    estado = HdEstado.objects.get(id=2)
                    form = HdIncidenciaFrom(initial={'estado':estado})
                    form.fields['grupo'].queryset = HdGrupo.objects.filter(pk=None)
                    form.fields['agente'].queryset = HdDetalle_Grupo.objects.filter(pk=None)
                    form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(pk=None)
                    form.fields['bloque'].queryset = HdBloque.objects.filter(status=True, hdbloqueubicacion__bloque__isnull=False).distinct('id')
                    form.fields['ubicacion'].queryset = HdBloqueUbicacion.objects.filter(pk=None)
                    form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=None)
                    form.fields['estado'].queryset = HdEstado.objects.filter(status=True, pk=1)
                    data['tiene_director'] = True if HdDirector.objects.filter(vigente=True).exists() else False
                    # form.adicionar_x_agente()
                    form.add()
                    data['form']=form
                    return render(request, "adm_hdagente/add.html", data)
                except Exception as ex:
                    pass

            if action == 'resolverincidente':
                try:
                    data['title'] = u'Resolver Incidente'
                    data['incidente'] = incidente = HdIncidente.objects.get(pk=int(request.GET['id']))
                    data['ordenpedidos'] = ordenpedidos = incidente.ordenpedidos.filter(anulado=False)
                    data['isOrdenpedidos'] = isOrdenpedidos = True if ordenpedidos.exists() else False
                    grupo = None
                    agente = None
                    categoria = None
                    subcategoria = None
                    ayudantes = None
                    data['destino'] = request.GET['destino']
                    if incidente.hddetalle_incidente_set.filter(status=True).exists():
                        ayudantes = HdDetalle_Grupo.objects.filter(pk__in=HdDetalle_Incidente_Ayudantes.objects.values_list('agente__id').filter(detallleincidente=incidente.ultimo_registro().id, status=True), status=True)
                        if incidente.ultimo_registro().estadoasignacion == 1:
                            if incidente.ultimo_registro().grupo:
                                grupo = incidente.ultimo_registro().grupo
                            if incidente.ultimo_registro().agente:
                                agente = incidente.ultimo_registro().agente
                        else:
                            agente = HdDetalle_Grupo.objects.filter(persona=persona, grupo__tipoincidente=incidente.tipoincidente)[0]
                            grupo = agente.grupo
                    else:
                        agente = HdDetalle_Grupo.objects.filter(persona=persona, grupo__tipoincidente=incidente.tipoincidente)[0]
                        grupo = agente.grupo
                    if incidente.subcategoria:
                        categoria = incidente.subcategoria.categoria
                        subcategoria = incidente.subcategoria
                    elif incidente.detallesubcategoria:
                        categoria = incidente.detallesubcategoria.subcategoria.categoria
                        subcategoria = incidente.detallesubcategoria.subcategoria
                    form = HdIncidenciaFrom(initial={'asunto': incidente.asunto,
                                                     'fechareporte': incidente.fechareporte,
                                                     'persona': incidente.persona.id,
                                                     'categoria': categoria,
                                                     'subcategoria': subcategoria,
                                                     'detallesubcategoria': incidente.detallesubcategoria if incidente.detallesubcategoria else None,
                                                     'prioridad':incidente.detallesubcategoria.prioridad.prioridad.nombre if incidente.detallesubcategoria else None,
                                                     'activo': incidente.activo.id if incidente.activo else 0,
                                                     'fechacompra': incidente.activo.fechaingreso if incidente.activo else None,
                                                     'vidautil': incidente.activo.vidautil if incidente.activo else None,
                                                     'tiemporestante': incidente.activo.fecha_caducidad() if incidente.activo else None,
                                                     'descripcion': incidente.descripcion,
                                                     'estado': HdEstado.objects.get(pk=2),
                                                     'agente': agente,
                                                     'grupo': grupo,
                                                     'bloque': incidente.ubicacion.bloque if incidente.ubicacion else None,
                                                     'ubicacion': incidente.ubicacion if incidente.ubicacion else None,
                                                     'tipoincidente': incidente.tipoincidente if incidente.tipoincidente else agente.grupo.tipoincidente,
                                                     'medioreporte': incidente.medioreporte,
                                                     'horareporte': incidente.horareporte,
                                                     'causa': incidente.causa,
                                                     'revisionequipoexterno': incidente.revisionequipoexterno,
                                                     'revisionequiposincodigo': incidente.revisionequiposincodigo,
                                                     'serie': incidente.serie,
                                                     'ayudantes': ayudantes
                                                     })
                    form.resolver()
                    if grupo:
                        if not ayudantes:
                            form.fields['ayudantes'].queryset = HdDetalle_Grupo.objects.filter(grupo=grupo).order_by('persona__apellido1')
                    if HdCausas.objects.filter(tipoincidente=incidente.tipoincidente,status=True).exists():
                        form.fields['causa'].queryset = HdCausas.objects.filter(pk__in=[1,4], tipoincidente=incidente.tipoincidente,status=True)
                    form.fields['estado'].queryset = HdEstado.objects.all().exclude(Q(id=1) | Q(id=4))
                    form.fields['persona'].widget.attrs['descripcion'] = incidente.persona
                    form.fields['persona'].widget.attrs['value'] = incidente.persona.id
                    # form.fields['departamento'].widget.attrs['descripcion'] = incidente.departamento if incidente.departamento else '------------------'
                    # form.fields['departamento'].widget.attrs['value'] = incidente.departamento.id if incidente.departamento else 0
                    if incidente.activo:
                        form.fields['activo'].widget.attrs['descripcion'] = incidente.activo
                        form.fields['activo'].widget.attrs['value'] = incidente.activo.id
                    else:
                        form.fields['activo'].widget.attrs['descripcion'] = '----------------'
                        form.fields['activo'].widget.attrs['value'] = 0
                    # if grupo.tipoincidente.id==1:
                    #     form.fields['categoria'].queryset = HdCategoria.objects.filter(status=True)
                    # else:
                    #     form.fields['categoria'].queryset = HdCategoria.objects.filter(tipoincidente=agente.grupo.tipoincidente)
                    if grupo.tipoincidente:
                        # form.fields['categoria'].queryset = HdCategoria.objects.filter(tipoincidente=agente.grupo.tipoincidente)
                        form.fields['categoria'].queryset = HdCategoria.objects.filter(tipoincidente=grupo.tipoincidente)
                    if incidente.detallesubcategoria:
                        form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(categoria=incidente.detallesubcategoria.subcategoria.categoria)
                        form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=incidente.detallesubcategoria_id)
                    elif incidente.subcategoria:
                        # form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(pk=None)
                        form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(categoria=incidente.subcategoria.categoria, status=True)
                        form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=None)
                    data['lista'] = incidente.mi_detalle()
                    es_tics = False
                    if grupo:
                        if not grupo.tipoincidente.id == 3:
                            es_tics = True
                    data['es_tics'] = es_tics
                    resuelto = False
                    if incidente.esta_resulto():
                        resuelto = True
                    data['resuelto'] = resuelto
                    if incidente.tipoincidente.id == 3:
                        data['materialesincidentes'] = incidente.hdmaterial_incidente_set.filter(status=True)
                        data['formmaterialesincidentes'] = HdMaterial_IncidenteForm()
                        data['materialesop'] = incidente.hdmaterial_ordenpedido_incidente_set.filter(status=True)
                    data['form'] = form
                    return render(request, "adm_hdagente/resolverincidente.html", data)
                except Exception as ex:
                    pass

            if action == 'reasignaragente':
                try:
                    data['title'] = u'Reasignar un Agente'
                    data['incidente'] = incidente = HdIncidente.objects.get(pk=int(request.GET['id']))
                    grupo = None
                    agente = None
                    data['destino'] = request.GET['destino']
                    if incidente.hddetalle_incidente_set.filter(status=True).exists():
                        if incidente.ultimo_registro().estadoasignacion == 1:
                            if incidente.ultimo_registro().grupo:
                                grupo = incidente.ultimo_registro().grupo
                            if incidente.ultimo_registro().agente:
                                agente = incidente.ultimo_registro().agente
                        else:
                            agente = HdDetalle_Grupo.objects.filter(persona=persona, grupo__tipoincidente=incidente.tipoincidente)[0]
                            grupo = agente.grupo
                    else:
                        agente = HdDetalle_Grupo.objects.filter(persona=persona, grupo__tipoincidente=incidente.tipoincidente)[0]
                        grupo = agente.grupo
                    form = HdIncidenciaFrom(initial={'asunto': incidente.asunto,
                                                     'fechareporte': incidente.fechareporte,
                                                     'persona': incidente.persona.id,
                                                     'categoria': incidente.detallesubcategoria.subcategoria.categoria if incidente.detallesubcategoria else None,
                                                     'subcategoria': incidente.detallesubcategoria.subcategoria if incidente.detallesubcategoria else None,
                                                     'detallesubcategoria': incidente.detallesubcategoria if incidente.detallesubcategoria else None,
                                                     'prioridad': incidente.detallesubcategoria.prioridad.prioridad.nombre if incidente.detallesubcategoria else None,
                                                     'activo': incidente.activo.id if incidente.activo else 0,
                                                     'fechacompra': incidente.activo.fechaingreso if incidente.activo else None,
                                                     'vidautil': incidente.activo.vidautil if incidente.activo else None,
                                                     'tiemporestante': incidente.activo.fecha_caducidad() if incidente.activo else None,
                                                     'descripcion': incidente.descripcion,
                                                     'estado': HdEstado.objects.filter(pk=2),
                                                     'grupo': grupo,
                                                     'bloque': incidente.ubicacion.bloque if incidente.ubicacion else None,
                                                     'ubicacion': incidente.ubicacion if incidente.ubicacion else None,
                                                     'tipoincidente': incidente.tipoincidente if incidente.tipoincidente else agente.grupo.tipoincidente,
                                                     'medioreporte': incidente.medioreporte,
                                                     'horareporte': incidente.horareporte
                                                     })
                    es_tics = False
                    if grupo:
                        form.fields['agente'].queryset = grupo.mis_agentes()
                        if grupo.tipoincidente.id == 2:
                            es_tics = True
                            form.fields['categoria'].queryset = HdCategoria.objects.filter(tipoincidente=grupo.tipoincidente, status=True)
                        else:
                            form.fields['categoria'].queryset = HdCategoria.objects.filter(status=True)
                    data['es_tics'] = es_tics
                    form.fields['grupo'].queryset = HdGrupo.objects.filter(status=True)
                    form.fields['persona'].widget.attrs['descripcion'] = incidente.persona
                    form.fields['persona'].widget.attrs['value'] = incidente.persona.id
                    if incidente.activo:
                        form.fields['activo'].widget.attrs['descripcion'] = incidente.activo
                        form.fields['activo'].widget.attrs['value'] = incidente.activo.id
                    else:
                        form.fields['activo'].widget.attrs['descripcion'] = '----------------'
                        form.fields['activo'].widget.attrs['value'] = 0
                    if incidente.detallesubcategoria:
                        form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(pk=incidente.detallesubcategoria.subcategoria_id)
                        form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=incidente.detallesubcategoria_id)
                    else:
                        form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(pk=None)
                        form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=None)
                    form.reasignar()
                    data['form']=form
                    return render(request, "adm_hdagente/reasignaragente.html", data)
                except Exception as ex:
                    pass

            if action == 'requerimientospiezapartes':
                try:
                    data['title'] = u'Requerimientos Piezas y Partes'
                    data['incidente'] = incidente = HdIncidente.objects.get(pk=int(request.GET['idincidente']))
                    data['requerimientospiezapartes'] = rpp = incidente.hdrequerimientospiezapartes_set.filter(status=True)
                    # data['detalle'] = RequerimientoPiezaParteMultiple.objects.filter(status=True, hdrequerimientospiezapartes__incidente=incidente.id)
                    data['detalle'] = RequerimientoPiezaParteMultiple.objects.filter(status=True, requerimiento__incidente_id=incidente.id)

                    return render(request, "adm_hdagente/requerimientospiezapartes.html", data)
                except Exception as ex:
                    pass

            if action == 'resolverrequerimiento':
                try:
                    data['title'] = u'Resolver requerimiento de Piezas y Partes'
                    data['requerimiento'] = requerimiento = HdRequerimientosPiezaPartes.objects.get(pk=int(request.GET['id']))
                    form = HdRequerimientosPiezaPartesForm(initial={'codigoresuelve':requerimiento.codigoresuelve,
                                                                    'observacionresuelve':requerimiento.observacionresuelve })
                    data['form'] = form
                    return render(request, "adm_hdagente/resolverrequerimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'addrequerimientopiezaparte':
                try:
                    data['title'] = u'Adicionar requerimiento de piezas y partes'
                    data['form'] = HdRequerimientoPiezaPartesForm
                    data['idincidente'] = HdIncidente.objects.get(pk=int(request.GET['idincidente']))
                    return render(request, "adm_hdagente/addrequerimientopiezaparte.html", data)
                except Exception as ex:
                    pass

            if action == 'delrequerimientopiezaparte':
                try:
                    data['title'] = u'Eliminar Requerimiento Pieza y Parte'
                    data['requerimiento'] = HdRequerimientosPiezaPartes.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_hdagente/delrequerimientopiezaparte.html", data)
                except Exception as ex:
                    pass

            if action == 'escalarincidente':
                try:
                    data['title'] = u'Escalar Incidente a otro Grupo'
                    data['incidente']= incidente = HdIncidente.objects.get(pk=int(request.GET['id']))
                    agente = None
                    data['destino'] = request.GET['destino']
                    if incidente.hddetalle_incidente_set.filter(status=True).exists():
                        if incidente.ultimo_registro().agente:
                            agente = incidente.ultimo_registro().agente
                    else:
                        agente = HdDetalle_Grupo.objects.filter(persona=persona, grupo__tipoincidente=incidente.tipoincidente)[0]
                    form = HdIncidenciaFrom(initial={'asunto': incidente.asunto,
                                                     'fechareporte': incidente.fechareporte,
                                                     'persona': incidente.persona.id,
                                                     'categoria': incidente.detallesubcategoria.subcategoria.categoria if incidente.detallesubcategoria else None,
                                                     'subcategoria': incidente.detallesubcategoria.subcategoria if incidente.detallesubcategoria else None,
                                                     'detallesubcategoria': incidente.detallesubcategoria if incidente.detallesubcategoria else None,
                                                     'prioridad': incidente.detallesubcategoria.prioridad.prioridad.nombre if incidente.detallesubcategoria else None,
                                                     'activo': incidente.activo.id if incidente.activo else 0,
                                                     'fechacompra': incidente.activo.fechaingreso if incidente.activo else None,
                                                     'vidautil': incidente.activo.vidautil if incidente.activo else None,
                                                     'tiemporestante': incidente.activo.fecha_caducidad() if incidente.activo else None,
                                                     'descripcion': incidente.descripcion,
                                                     'bloque': incidente.ubicacion.bloque if incidente.ubicacion else None,
                                                     'ubicacion': incidente.ubicacion if incidente.ubicacion else None,
                                                     'tipoincidente': incidente.tipoincidente if incidente.tipoincidente else agente.grupo.tipoincidente,
                                                     'medioreporte': incidente.medioreporte,
                                                     'horareporte': incidente.horareporte
                                                     })
                    es_tics = False
                    if not incidente.tipoincidente.id==3:
                        es_tics = True
                    data['es_tics'] = es_tics
                    form.fields['tipoincidente'].queryset = HdTipoIncidente.objects.filter(status=True).exclude(pk=agente.grupo.tipoincidente.id)
                    form.fields['persona'].widget.attrs['descripcion'] = incidente.persona
                    form.fields['persona'].widget.attrs['value'] = incidente.persona.id
                    if incidente.activo:
                        form.fields['activo'].widget.attrs['descripcion'] = incidente.activo
                        form.fields['activo'].widget.attrs['value'] = incidente.activo.id
                    else:
                        form.fields['activo'].widget.attrs['descripcion'] = '----------------'
                        form.fields['activo'].widget.attrs['value'] = 0
                    # if grupo.tipoincidente:
                    #     form.fields['categoria'].queryset = HdCategoria.objects.filter(tipoincidente=agente.grupo.tipoincidente)
                    # if incidente.detallesubcategoria:
                    #     form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(categoria=incidente.detallesubcategoria.subcategoria.categoria)
                    #     form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=incidente.detallesubcategoria_id)
                    # elif incidente.subcategoria:
                    #     form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(categoria=incidente.subcategoria.categoria, status=True)
                    #     form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=None)

                    if incidente.subcategoria:
                        form.fields['categoria'].queryset = HdCategoria.objects.filter(tipoincidente=incidente.tipoincidente)
                        form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(pk=incidente.detallesubcategoria.subcategoria_id if incidente.detallesubcategoria else None)
                        form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=incidente.detallesubcategoria_id if incidente.detallesubcategoria_id else None)
                    else:
                        form.fields['categoria'].queryset = HdCategoria.objects.filter(tipoincidente=incidente.tipoincidente)
                        form.fields['subcategoria'].queryset = HdSubCategoria.objects.filter(pk=None)
                        form.fields['detallesubcategoria'].queryset = HdDetalle_SubCategoria.objects.filter(pk=None)
                    form.escalar()
                    data['form'] = form
                    return render(request, "adm_hdagente/escalarincidente.html", data)
                except Exception as ex:
                    pass

            if action == 'listaordentrabajo':
                try:
                    data['title'] = u'Orden de trabajo'
                    search = None
                    ids = None
                    tipo = None
                    idordenes = HdDetalle_Incidente.objects.filter(status=True, agente__persona=persona).values_list('incidente__ordentrabajo__id', flat=True)
                    ordenes = OrdenTrabajo.objects.filter(status=True, id__in =idordenes )
                    if 's' in request.GET:
                        search = request.GET['s']
                        ordenes = ordenes.filter(Q(codigoorden__icontains=search))
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        ordenes = ordenes.filter(id=ids)
                    paging = MiPaginador(ordenes, 25)
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
                    data['ordenes'] = page.object_list
                    return render(request, "adm_hdagente/listaordentrabajo.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrarorden':
                try:
                    data['title'] = u'Cerrar orden de trabajo'
                    data['orden'] = orden = OrdenTrabajo.objects.get(pk=int(request.GET['id']))
                    data['detalleorden'] = orden.detalleordentrabajo_set.filter(status=True)
                    initial=  model_to_dict(orden)
                    data['form'] = form = CerrarOrdenForm(initial=initial)
                    data['form2'] = DetalleOrdenForm()
                    return render(request, "adm_hdagente/cerrarorden.html", data)
                except Exception as ex:
                    pass

            if action == 'addodenpedido':
                try:
                    data['title'] = u'Generar Orden de Pedido'
                    data['incidete'] = incidete = HdIncidente.objects.get(id=int(request.GET['id']))

                    ultimo = 1
                    try:
                        ultimo = OrdenPedido.objects.all().order_by("-id")[0].numerodocumento
                        ultimo = int(ultimo) + 1
                    except:
                        pass
                    ultimo = generar_codigo(ultimo, PREFIX, SUFFIX, 9, True)
                    # distributivo = DistributivoPersona.objects.filter(status=True, persona=persona)[0]
                    descripcion = ("Solicitud de pedidos de materiales para la orden de pedido Nro. %s solicitado por %s" % (incidete.ordentrabajo.codigoorden, incidete.persona))
                    form = OrdenPedidoForm(initial={'codigodocumento': ultimo,
                                                    'fechaordenpedido': datetime.now().date(),
                                                    'responsable': persona,
                                                    'descripcion': descripcion})

                    form.addOrdenTrabajo()
                    data['form'] = form
                    form2 = DetalleOrdenPedidoForm()
                    form2.adicionar()
                    data['form2'] = form2
                    data['title'] = u'Nueva orden de pedido'
                    data['return'] = 'adm_hdagente'
                    return render(request, "adm_hdagente/addOrdenPedido.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Gestión Incidentes Asignados'
                searchg = None
                search = None
                ids = None
                idsg = None
                estg = 0
                est = 0
                selecttipoeq = 0
                selecttipoeqg = 0
                if persona.hddetalle_grupo_set.filter(status=True, estado=True):
                    agente = HdDetalle_Grupo.objects.get(persona=persona, status=True)
                    data['esdemantenimiento'] = True if agente.grupo.tipoincidente.id == 3 else False
                    incidentegrupales = HdIncidente.objects.filter(Q(status=True) & Q(tipoincidente=agente.grupo.tipoincidente)).order_by('estado__id', '-fechareporte').distinct()
                    if 'tipo_equipog' in request.GET:
                        selecttipoeqg = int(request.GET['tipo_equipog'])
                        if selecttipoeqg ==1:
                            incidentegrupales = incidentegrupales.filter(revisionequiposincodigo=True)
                        if selecttipoeqg == 2:
                            incidentegrupales = incidentegrupales.filter(revisionequipoexterno=True)
                        if selecttipoeqg == 3:
                            incidentegrupales = incidentegrupales.filter(ordentrabajo__codigoorden__isnull=False)
                        if selecttipoeqg == 4:
                            incidentegrupales = incidentegrupales.filter(ordentrabajo__codigoorden__isnull=True)
                        # else:
                        #     incidentegrupales = incidentegrupales.filter(revisionequipoexterno=True)
                    if 'estg' in request.GET:
                        estg = int(request.GET['estg'])
                        incidentegrupales = incidentegrupales.filter(estado_id=estg)
                    if 'idg' in request.GET:
                        idsg = request.GET['idg']
                        incidentegrupales = incidentegrupales.filter(pk=idsg)
                    if 'sg' in request.GET:
                        searchg = request.GET['sg']
                        ss = searchg.split(' ')
                        if len(ss) == 1:
                            incidentegrupales = incidentegrupales.filter((Q(persona__nombres__icontains=searchg) |Q(persona__apellido1__icontains=searchg) | Q(persona__apellido2__icontains=searchg) | Q(asunto__icontains=searchg)))
                        else:
                            incidentegrupales = incidentegrupales.filter((Q(persona__nombres__icontains=ss[0]) & Q(persona__apellido1__icontains=ss[1])) |(Q(persona__apellido1__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1])) | (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])) | (Q(asunto__icontains=ss[0]) & Q(asunto__icontains=ss[1])))
                    paging_grupo = MiPaginador(incidentegrupales, 20)
                    pg = 1
                    try:
                        paginasesion_grupo = 1
                        if 'paginador' in request.session:
                            paginasesion_grupo = int(request.session['paginador'])
                        if 'page_grupo' in request.GET:
                            pg = int(request.GET['page_grupo'])
                        else:
                            pg = paginasesion_grupo
                        try:
                            page_grupo = paging_grupo.page(pg)
                        except:
                            pg = 1
                        page_grupo = paging_grupo.page(pg)
                    except:
                        page_grupo = paging_grupo.page(pg)
                    request.session['paginador'] = pg
                    data['paging_grupo'] = paging_grupo
                    data['rangospaging_grupo'] = paging_grupo.rangos_paginado(pg)
                    data['page_grupo'] = page_grupo
                    data['searchg'] = searchg if searchg else ""
                    data['idsg'] = idsg if idsg else ""
                    data['migrupo'] = page_grupo.object_list
                    data['estadoidg'] = estg
                    data['selecttipoeqg'] = selecttipoeqg
                    # mis incidentes
                    incidentes = HdIncidente.objects.filter(Q(status=True), Q(hddetalle_incidente__agente=agente), Q(hddetalle_incidente__estadoasignacion=1)).order_by('estado_id', '-fechareporte').distinct()
                    if 'tipo_equipo' in request.GET:
                        selecttipoeq = int(request.GET['tipo_equipo'])
                        if selecttipoeq ==1:
                            incidentes = incidentes.filter(revisionequiposincodigo=True)
                        if selecttipoeq == 2:
                            incidentes = incidentes.filter(revisionequipoexterno=True)
                        if selecttipoeq == 3:
                            incidentes = incidentes.filter(ordentrabajo__codigoorden__isnull=False)
                        if selecttipoeq == 4:
                            incidentes = incidentes.filter(ordentrabajo__codigoorden__isnull=True)
                    if 'est' in request.GET:
                        est = int(request.GET['est'])
                        incidentes = incidentes.filter(estado=est)
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        incidentes = incidentes.filter(pk=ids)
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            if 'tipo_equipo' in request.GET:
                                selecttipoeq = int(request.GET['tipo_equipo'])
                                if selecttipoeq == 3:
                                    incidentes = incidentes.filter((Q(ordentrabajo__codigoorden__icontains=search)))
                                else:
                                    incidentes = incidentes.filter(Q(persona__nombres__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(asunto__icontains=search)| Q(pk__icontains=search))
                            else:
                                incidentes = incidentes.filter(Q(persona__nombres__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(asunto__icontains=search)| Q(pk__icontains=search))
                        else:
                            incidentes = incidentes.filter((Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])) | (Q(asunto__icontains=ss[0]) & Q(asunto__icontains=ss[1])))
                    paging = MiPaginador(incidentes, 20)
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
                    data['misincidentes'] = page.object_list
                    data['administrativo'] = persona
                    data['estados'] = HdEstado.objects.all()
                    data['estadoid'] = est
                    data['selecttipoeq'] = selecttipoeq
                    data['persona_id'] = persona.id
                    data['form2'] = SeleccionarActivoForm()
                    data['reporte_0'] = obtener_reporte('reporte_incidente')
                    data['cargo'] = '(' + persona.distributivopersona_set.filter(status=True, estadopuesto=1)[0].denominacionpuesto.descripcion + ')' if persona.distributivopersona_set.filter(status=True, estadopuesto=1) else ''
                    data['cant_mis_incidentes'] = HdIncidente.objects.filter(Q(hddetalle_incidente__agente=agente), Q(status=True), (Q(estado=1)|Q(estado=2))).exclude(Q(hddetalle_incidente__estadoasignacion=3) | Q(hddetalle_incidente__estadoasignacion=4)).count()
                    data['cant_todos'] = HdIncidente.objects.filter(Q(status=True), Q(tipoincidente=agente.grupo.tipoincidente), (Q(estado_id=1)| Q(estado_id=2))).count()
                else:
                    return HttpResponseRedirect("/?info=No se encuentra registrado como agente de Help Desk.")
                return render(request, "adm_hdagente/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/?info=Error al cargar los datos.")


