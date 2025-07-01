# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.db.models.query_utils import Q
from decorators import secure_module, last_access
from helpdesk.forms import HdSolicitarIncidenteFrom
from helpdesk.models import HdIncidente, \
    HdBloqueUbicacion, HdSubCategoria, HdDetalle_SubCategoria, HdDetEncuestas, HdRespuestaEncuestas, \
    HdCabRespuestaEncuestas, ActivoFijo, HdGrupo, HdCategoria, HdCausas, HdTipoIncidente,ActivosSinCodigo
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import Persona
from sagest.models import HdBloque
from sga.templatetags.sga_extras import encrypt
#
# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addsolicitud':
            try:
                form = HdSolicitarIncidenteFrom(request.POST, request.FILES)
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
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf, jpg, png, jpeg."})
                if form.is_valid():
                    getactivo=None
                    getactivosincodigo=None
                    responsableactivofijo=None
                    responsableactivofijosincod=None
                    tercerapersona=None
                    tipousuario = 1
                    perfilprin = request.session['perfilprincipal']
                    if perfilprin.es_profesor():
                        tipousuario = 2
                    if 'tipousuario' in request.POST:
                        tipousuario = request.POST['tipousuario']
                    if 'tercerapersona' in request.POST:
                        tercerapersona = request.POST['tercerapersona']
                    if len(request.POST['activo']) > 0:
                        if int(request.POST['activo']) > 0:
                            getactivo = ActivoFijo.objects.get(pk=int(request.POST['activo']))

                            responsableactivofijo = getactivo.responsable

                    if len(request.POST['activosincodigo']) > 0:
                        if int(request.POST['activosincodigo']) > 0:
                            getactivosincodigo = ActivosSinCodigo.objects.get(pk=int(request.POST['activosincodigo']))

                            responsableactivofijosincod = getactivosincodigo.responsable




                    incidente = HdIncidente(asunto=form.cleaned_data['asunto'],
                                            ubicacion_id=int(request.POST['ubicacion']),
                                            persona_id=persona.id,
                                            fechareporte=datetime.now().date(),
                                            horareporte=datetime.now().time(),
                                            medioreporte_id=4,
                                            estado_id=1,
                                            tercerapersona_id=tercerapersona,
                                            tipoincidente_id=int(request.POST['tipoincidente']) if 'tipoincidente' in request.POST else 3,
                                            activo=getactivo if getactivo else getactivo,
                                            responsableactivofijo=responsableactivofijo if responsableactivofijo else responsableactivofijosincod,
                                            archivo=newfile,
                                            tipousuario=tipousuario,
                                            activosincodigo = getactivosincodigo if getactivosincodigo else getactivosincodigo,
                                            concodigo = form.cleaned_data['concodigo']
                                            )
                    incidente.save(request)
                    if incidente.tipoincidente_id == 3:
                        incidente.email_notificacion_mantenimiento()
                        #los correros

                    log(u'Adiciono nueva solicitud: %s' % incidente, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action=='editsolicitud':
            try:
                incidente = HdIncidente.objects.get(pk=int(request.POST['id']))
                form = HdSolicitarIncidenteFrom(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            whitelist = ['.pdf', '.jpg', '.png', '.jpeg', '.PDF', '.JPG', '.PNG', '.JPEG']
                            if not ext in whitelist:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf, jpg, png, jpeg."})

                if form.is_valid():
                    getactivo, getactivosincodigo, responsableactivofijo, responsableactivofijosincod, tercerapersona = None, None, None, None, None
                    tipousuario = 1
                    perfilprin = request.session['perfilprincipal']
                    if perfilprin.es_profesor():
                        tipousuario = 2
                    if 'tipousuario' in request.POST:
                        tipousuario = request.POST['tipousuario']
                    if 'tercerapersona' in request.POST:
                        tercerapersona = request.POST['tercerapersona']

                    if int(request.POST.get('activo', 0)):
                        getactivo = ActivoFijo.objects.get(pk=int(request.POST['activo']))
                        responsableactivofijo = getactivo.responsable

                    if int(request.POST.get('activosincodigo', 0)):
                        getactivosincodigo = ActivosSinCodigo.objects.get(pk=int(request.POST['activosincodigo']))
                        responsableactivofijosincod = getactivosincodigo.responsable

                    incidente.tipousuario = tipousuario
                    incidente.asunto=form.cleaned_data['asunto']
                    incidente.ubicacion_id=int(request.POST['ubicacion'])
                    incidente.persona_id=persona.id
                    incidente.tercerapersona_id=tercerapersona
                    incidente.tipoincidente_id=int(request.POST.get('tipoincidente', 1))
                    incidente.activo = getactivo if getactivo else getactivo
                    incidente.responsableactivofijo = responsableactivofijo if responsableactivofijo else responsableactivofijosincod
                    incidente.activosincodigo = getactivosincodigo if getactivosincodigo else getactivosincodigo
                    #incidente.concodigo = form.cleaned_data.get('concodigo')

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("estadohelpdesk_", newfile._name)
                        incidente.archivo = newfile
                    incidente.save(request)

                    log(u'Edito solicitud de incidente: %s' % incidente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({'result':False, "form": [{k: v[0]} for k, v in form.errors.items()]})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delsolicitud':
            try:
                incidente = HdIncidente.objects.get(pk=int(request.POST['id']))
                if not incidente.tiene_detalle():
                    incidente.delete()
                    log(u'Elimino la solicitud de incidente: %s' % incidente, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "ok", "mensaje": u"No se puede eliminar, el registro ese encuentra activo.."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

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

        if action == 'selectgrupos':
            try:
                if 'id' in request.POST:
                    lista = []
                    listacategoria = []
                    listacausas = []
                    mi_tipo = False
                    grupos = HdGrupo.objects.filter(tipoincidente_id=int(request.POST['id']), status=True)
                    categorias = HdCategoria.objects.filter(tipoincidente_id=int(request.POST['id']), status=True)
                    causas = HdCausas.objects.filter(tipoincidente_id=int(request.POST['id']), status=True)
                    for grupo in grupos:
                        lista.append([grupo.id, grupo.nombre])
                    if causas:
                        for causa in causas:
                            listacausas.append([causa.id, causa.nombre])
                    for categoria in categorias:
                        listacategoria.append([categoria.id, categoria.nombre])
                    if int(request.POST['id']) == 2 or int(request.POST['id']) == 1:
                        mi_tipo = True
                    return JsonResponse({"result": "ok", 'lista': lista, 'listacausas': listacausas, 'listacategoria': listacategoria, 'mi_tipo': mi_tipo, 'es_tics': True if int(request.POST['id'])== 2 else False})
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

        if action == 'realizarencuesta':
            try:
                incidente = HdIncidente.objects.get(pk=int(encrypt(request.POST['incidente'])))
                mantexterno = False
                if 'mantexterno' in request.POST:
                    mantexterno = True if request.POST['mantexterno']=='true' else False
                if incidente.revisionequipoexterno:
                    if not mantexterno:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe certificar que que recibio mantenimiento a un equipo externo."})
                cabeceraencuesta = HdCabRespuestaEncuestas(incidente=incidente,fecha_encuesta=datetime.now(), mantenimientoexterno=mantexterno)
                cabeceraencuesta.save(request)
                for elemento in request.POST['lista'].split(','):
                    individuales = elemento.split('_')
                    iddeencuesta = individuales[0]
                    idrespuesta = individuales[1]
                    id_observacion = individuales[2]
                    if not HdRespuestaEncuestas.objects.filter(cabrespuesta=cabeceraencuesta,detencuesta_id=iddeencuesta).exists():
                        respuestaencuesta = HdRespuestaEncuestas(cabrespuesta=cabeceraencuesta,
                                                                 detencuesta_id=iddeencuesta,
                                                                 observaciones=id_observacion,
                                                                 respuesta_id=idrespuesta)
                        respuestaencuesta.save(request)
                incidente.realizoencuesta = True
                incidente.save(request)
                log(u'Realizo encuesta: %s' % incidente, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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

        if action == 'selecttipoincidente':
            try:
                if 'id' in request.POST:
                    lista = []
                    if int(request.POST['id']) == 1:
                        tiposincidentes = HdTipoIncidente.objects.filter(pk__in=[2,3], status=True)
                    if int(request.POST['id']) == 2:
                        tiposincidentes = HdTipoIncidente.objects.filter(pk=1, status=True)
                    for tip in tiposincidentes:
                        lista.append([tip.id, tip.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        if action == 'detalle_incidente':
            try:
                if 'id' in request.POST:
                    data['incidente'] = incidente = HdIncidente.objects.get(pk=int(request.POST['id']), status=True)
                    data['puede_vizualisar_detalle'] = True if incidente.mi_detalle().count()>1 else False
                    if incidente.usuario_creacion:
                        data['personacreacion'] = Persona.objects.get(usuario=incidente.usuario_creacion) if incidente.usuario_creacion.id > 1 else ""
                    if incidente.activo:
                        fecha = datetime.strftime(incidente.activo.fechaingreso, '%Y-%m-%d')
                        vfecha = fecha.split('-')
                        vfecha[0] = str(int(vfecha[0]) + incidente.activo.vidautil)
                        data['fechacaducidad'] = str(vfecha[0] + '/' + vfecha[1] + '/' + vfecha[2])
                    template = get_template("helpdesk_hdusuario/modaldetalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'tipogrupo':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                lista = []
                if persona.es_profesor():
                    listado = HdTipoIncidente.objects.filter(pk=1)
                else:
                    listado = HdTipoIncidente.objects.filter(pk__in=[2,3])
                for lis in listado:
                    lista.append([lis.id, lis.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})



        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'addsolicitud':
                try:
                    data['title'] = u'Adicionar Solicitud'
                    form = HdSolicitarIncidenteFrom()
                    form.fields['bloque'].queryset = HdBloque.objects.filter(status=True, hdbloqueubicacion__bloque__isnull=False).distinct('id')
                    form.fields['ubicacion'].queryset = HdBloqueUbicacion.objects.filter(pk=None)
                    data['perfilprin'] = perfilprin = request.session['perfilprincipal']
                    if perfilprin.es_profesor():
                        form.es_docente()
                    else:
                        dispersona = persona.distributivopersona_set.filter(estadopuesto_id=1, status=1)
                        if dispersona.count()==1:
                            form.desactiva_tipousuario()
                            form.fields['tipoincidente'].queryset = HdTipoIncidente.objects.filter(pk__in=[3])

                    if persona.hdpersona.filter(estado=True, status=True):
                        grupoincidente = persona.hdpersona.filter(estado=True, status=True)[0]
                        if grupoincidente.grupo.id!=4:
                            if not perfilprin.es_profesor():
                                form.desactivar()
                    else:
                        form.desactivar()
                    data['form'] = form
                    return render(request, "helpdesk_hdusuario/addsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'editsolicitud':
                try:
                    data['title'] = u'Editar registro de incidente'
                    data['incidente'] = solicitud = HdIncidente.objects.get(pk=int(request.GET['id']))
                    data['perfilprin'] = perfilprin = request.session['perfilprincipal']
                    if perfilprin.es_profesor():
                        form = HdSolicitarIncidenteFrom(initial={'tipousuario': solicitud.tipousuario,
                                                                 'bloque': solicitud.ubicacion.bloque if solicitud.ubicacion.bloque else None,
                                                                 'ubicacion': solicitud.ubicacion if solicitud.ubicacion else None,
                                                                 'asunto': solicitud.asunto,
                                                                 })
                    else:
                        form = HdSolicitarIncidenteFrom(initial={'tipousuario': solicitud.tipousuario,
                                                                 'bloque': solicitud.ubicacion.bloque if solicitud.ubicacion.bloque else None,
                                                                 'ubicacion': solicitud.ubicacion if solicitud.ubicacion else None,
                                                                 'asunto': solicitud.asunto,
                                                                 'tipoincidente': solicitud.tipoincidente if solicitud.tipoincidente else None,
                                                                 })
                    if solicitud.activo:
                        form.editar(solicitud.activo)
                    if perfilprin.es_profesor():
                        form.es_docente()
                    else:
                        dispersona = persona.distributivopersona_set.filter(estadopuesto_id=1, status=1)
                        if dispersona.count() == 1:
                            form.desactiva_tipousuario()
                        
                    activarselect = 0
                    if persona.hdpersona.filter(estado=True, status=True):
                        grupoincidente = persona.hdpersona.filter(estado=True, status=True)[0]
                        if grupoincidente.grupo.id != 4:
                            if not perfilprin.es_profesor():
                                form.desactivar()
                                activarselect = 1
                    else:
                        form.desactivar()

                    form.cargarubicacion(solicitud.ubicacion.bloque)
                    data['form'] = form
                    data['activarselect'] = activarselect
                    # form.fields['ubicacion'].initial = solicitud.ubicacion
                    return render(request, "adm_hdusuario/editsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar registro de incidente'
                    data['incidente'] = HdIncidente.objects.get(pk=int(request.GET['id']))
                    return render(request, "helpdesk_hdusuario/delsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'realizarencuesta':
                try:
                    data['title'] = u'Encuesta'
                    data['incidente'] = incidente = HdIncidente.objects.get(pk=int(encrypt(request.GET['idincidente'])))
                    data['agente'] = incidente.h_d_incidentes.filter(estado=3,status=True).order_by('-id')[0].agente
                    data['listadopreguntas'] = HdDetEncuestas.objects.filter(encuesta__tipoincidente_id=incidente.tipoincidente.id,encuesta__activo=True,encuesta__status=True,activo=True,status=True)
                    return render(request, "helpdesk_hdusuario/realizarencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscaractivo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    tipo = int(request.GET['idt'])
                    if persona.usuario.is_superuser:
                        if s.__len__() == 1:
                            # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                            activo = ActivoFijo.objects.filter(
                                Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(
                                    serie__icontains=q), status=True).distinct()[:20]
                        else:
                            activo = ActivoFijo.objects.filter(
                                (Q(codigogobierno__icontains=s[0]) & Q(codigointerno__icontains=s[1])) |
                                (Q(codigogobierno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                                (Q(codigogobierno__icontains=s[0]) & Q(descripcion__icontains=s[1])) |
                                (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1])) |
                                (Q(codigointerno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                                # (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                                (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(
                                status=True).distinct()[:20]

                    else:
                            if s.__len__() == 1:
                                # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                                activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True,responsable=persona.pk).distinct()[:20]
                            else:
                                activo = ActivoFijo.objects.filter((Q(codigogobierno__icontains=s[0])& Q(codigointerno__icontains=s[1]))|
                                                                   (Q(codigogobierno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                                                                   (Q(codigogobierno__icontains=s[0]) & Q(descripcion__icontains=s[1])) |
                                                                   (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1])) |
                                                                   (Q(codigointerno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                                                                   # (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                                                                   (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True,responsable=persona.pk).distinct()[:20]


                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_reprhd()} for x in activo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'buscaractivosincodigo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    tipo = int(request.GET['idt'])
                    if persona.usuario.is_superuser:
                        if s.__len__() == 1:
                            # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                            activo = ActivosSinCodigo.objects.filter(
                                Q(codigointerno__icontains=s[0]) | Q(
                                    serie__icontains=q), status=True).distinct()[:20]
                        else:
                            activo = ActivosSinCodigo.objects.filter(
                                ( Q(codigointerno__icontains=s[1])) |
                                ( Q(serie__icontains=s[1])) |
                                ( Q(descripcion__icontains=s[1])) |
                                (Q(codigointerno__icontains=s[0]) & Q(serie__icontains=s[1]))
                                # (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                            ).filter(
                                status=True).distinct()[:20]

                    else:
                            if s.__len__() == 1:
                                # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                                activo = ActivosSinCodigo.objects.filter(Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True,responsable=persona.pk).distinct()[:20]
                            else:
                                activo = ActivosSinCodigo.objects.filter((Q(codigointerno__icontains=s[1]))|
                                                                   ( Q(serie__icontains=s[1])) |
                                                                   ( Q(descripcion__icontains=s[1])) |
                                                                   (Q(codigointerno__icontains=s[0]) ) |
                                                                   (Q(codigointerno__icontains=s[0]) & Q(serie__icontains=s[1]))
                                                                   # (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                                                                 ).filter(status=True,responsable=persona.pk).distinct()[:20]


                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_reprhd()} for x in activo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect("/adm_hdincidente")

        else:
            data['title'] = u'Registro de incidentes'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    incidentes = HdIncidente.objects.filter(asunto__icontains=search, status=True, persona_id=persona.id).order_by('estado_id')
                elif len(ss) == 2:
                    incidentes = HdIncidente.objects.filter(Q(asunto__icontains=ss[0]), Q(asunto__icontains=ss[1]), Q(status=True), Q(persona_id=persona.id)).order_by('estado_id')
                else:
                    incidentes = HdIncidente.objects.filter(Q(asunto__icontains=ss[0]) , Q(asunto__icontains=ss[1]), Q(asunto__icontains=ss[1]), Q(status=True), Q(persona_id=persona.id)).order_by('estado_id')
            elif 'id' in request.GET:
                ids = request.GET['id']
                incidentes = HdIncidente.objects.filter(id=ids, status=True,persona_id=persona.id).order_by('estado_id')
            else:
                incidentes = HdIncidente.objects.filter(status=True,persona_id=persona.id).order_by('estado_id')
            paging = MiPaginador(incidentes, 10)
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
            data['incidentes'] = page.object_list
            data['faltantes'] = 0
            if HdDetEncuestas.objects.filter(encuesta__tipoincidente_id=2, encuesta__activo=True, encuesta__status=True, activo=True, status=True).exists():
                data['faltantes'] = incidentes.filter(tipoincidente_id=2, estado=3, realizoencuesta=False).count()
            data['administrativo'] = persona
            return render(request, "helpdesk_hdusuario/view.html", data)


