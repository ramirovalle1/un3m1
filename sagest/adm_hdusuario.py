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
from sagest.forms import HdSolicitarIncidenteFrom
from sagest.models import HdIncidente, HdBloque, \
    HdBloqueUbicacion, HdSubCategoria, HdDetalle_SubCategoria, HdDetEncuestas, HdRespuestaEncuestas, \
    HdCabRespuestaEncuestas, ActivoFijo, HdGrupo, HdCategoria, HdCausas, HdDetalle_Grupo, HdTipoIncidente
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import Persona
from sga.templatetags.sga_extras import encrypt
from helpdesk import models as hd

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
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
                    getactivo, responsableactivofijo, tipousuario = None, None, 1
                    perfilprin = request.session['perfilprincipal']
                    if perfilprin.es_profesor():
                        tipousuario = 2

                    if len(request.POST['activo']) > 0:
                        if int(request.POST['activo']) > 0:
                            getactivo = ActivoFijo.objects.get(pk=int(request.POST['activo']))
                            responsableactivofijo = getactivo.responsable

                    tipoincidente = int(request.POST.get('tipoincidente', 1))
                    values_to_save = {
                            'asunto': form.cleaned_data['asunto'],
                            'ubicacion_id': int(request.POST['ubicacion']),
                            'persona_id': persona.id,
                            'fechareporte': datetime.now().date(),
                            'horareporte': datetime.now().time(),
                            'medioreporte_id': 4,
                            'estado_id': 1,
                            'tercerapersona': persona,
                            'tipoincidente_id': tipoincidente,
                            'activo': getactivo if getactivo else getactivo,
                            'responsableactivofijo': responsableactivofijo,
                            'archivo': newfile,
                            'tipousuario': tipousuario,
                    }

                    if tipoincidente == 2:
                        incidente = hd.HdIncidente(**values_to_save)
                    else:
                        incidente = HdIncidente(**values_to_save)

                    incidente.save(request)
                    if tipoincidente == 3:
                        incidente.email_notificacion_mantenimiento()

                    if tipoincidente == 4:
                        incidente.email_notificacion_seguridadinformatica()

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
                            if ext == '.pdf' or ext == '.jpg' or ext == '.png' or ext == '.jpeg' or ext == '.PDF' or ext == '.JPG' or ext == '.PNG' or ext == '.JPEG':
                                a = 1
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf, jpg, png, jpeg."})
                if form.is_valid():
                    getactivo=None
                    responsableactivofijo=None
                    tercerapersona = None
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
                    incidente.tipousuario = tipousuario
                    incidente.asunto=form.cleaned_data['asunto']
                    incidente.ubicacion_id=int(request.POST['ubicacion'])
                    incidente.persona_id=persona.id
                    incidente.tercerapersona_id=tercerapersona
                    incidente.tipoincidente_id=int(request.POST['tipoincidente']) if 'tipoincidente' in request.POST else 1
                    incidente.activo = getactivo if getactivo else getactivo
                    incidente.responsableactivofijo = responsableactivofijo
                    # incidente.activosincodigo = form.cleaned_data['activosincodigo']
                    # incidente.concodigo = form.cleaned_data['concodigo']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("estadohelpdesk_", newfile._name)
                        incidente.archivo = newfile
                    incidente.save(request)
                    log(u'Edito solicitud de incidente: %s' % incidente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
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
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar, el registro se encuentra activo."})
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
                    incidente = None
                    if int(request.POST.get('tipoincidente', 0)) == 2:
                        incidente = hd.HdIncidente.objects.get(pk=int(request.POST['id']), status=True)
                    else:
                        incidente = HdIncidente.objects.get(pk=int(request.POST['id']), status=True)

                    data['incidente'] = incidente
                    data['puede_vizualisar_detalle'] = incidente.mi_detalle().count() > 1

                    if incidente.usuario_creacion:
                        data['personacreacion'] = Persona.objects.get(usuario=incidente.usuario_creacion) if incidente.usuario_creacion.id > 1 else ""
                    if incidente.activo:
                        fecha = datetime.strftime(incidente.activo.fechaingreso, '%Y-%m-%d')
                        vfecha = fecha.split('-')
                        vfecha[0] = str(int(vfecha[0]) + incidente.activo.vidautil)
                        data['fechacaducidad'] = str(vfecha[0] + '/' + vfecha[1] + '/' + vfecha[2])
                    template = get_template("adm_hdusuario/modaldetalle.html")
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
                    #form.fields['ubicacion'].queryset = HdBloqueUbicacion.objects.filter(pk=None)
                    data['perfilprin'] = perfilprin = request.session.get('perfilprincipal')
                    #if perfilprin.es_administrativo(): form.fields['tipousuario'].initial = 1
                    if perfilprin.es_profesor():
                        form.es_docente()
                    else:
                        if persona.distributivopersona_set.values('id').filter(estadopuesto_id=1, status=1).exists():
                            form.desactiva_tipousuario()
                            form.fields['tipoincidente'].queryset = HdTipoIncidente.objects.filter(pk__in=[2,3,4])

                    if persona.hddetalle_grupo_set.values('id').filter(estado=True, status=True).exists():
                        grupoincidente = persona.hddetalle_grupo_set.filter(estado=True, status=True)[0]
                        if grupoincidente.grupo.id != 4 and not perfilprin.es_profesor():
                            form.desactivar()
                    else:
                        form.desactivar()
                    data['form'] = form
                    return render(request, "adm_hdusuario/addsolicitud.html", data)
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
                                                                 # 'concodigo': solicitud.concodigo,
                                                                 # 'activosincodigo': solicitud.activosincodigo if solicitud.activosincodigo else None
                                                                 })
                    else:
                        form = HdSolicitarIncidenteFrom(initial={'tipousuario': solicitud.tipousuario,
                                                                 'bloque': solicitud.ubicacion.bloque if solicitud.ubicacion.bloque else None,
                                                                 'ubicacion': solicitud.ubicacion if solicitud.ubicacion else None,
                                                                 'asunto': solicitud.asunto,
                                                                 'tipoincidente': solicitud.tipoincidente if solicitud.tipoincidente else None,
                                                                 # 'concodigo': solicitud.concodigo,
                                                                 # 'activosincodigo': solicitud.activosincodigo if solicitud.activosincodigo else None
                                                                 })

                    if solicitud.activo:
                        form.editar(solicitud.activo)
                    if perfilprin.es_profesor():
                        form.es_docente()
                    else:
                        dispersona = persona.distributivopersona_set.filter(estadopuesto_id=1, status=1)
                        if dispersona.count()==1:
                            form.desactiva_tipousuario()
                        else:
                            if solicitud.tipousuario==1:
                                form.fields['tipoincidente'].queryset = HdTipoIncidente.objects.filter(pk__in=[2,3,4])
                            if solicitud.tipousuario==2:
                                form.fields['tipoincidente'].queryset = HdTipoIncidente.objects.filter(pk=1)
                    activarselect = 0
                    if persona.hddetalle_grupo_set.filter(estado=True, status=True):
                        grupoincidente = persona.hddetalle_grupo_set.filter(estado=True, status=True)[0]
                        if grupoincidente.grupo.id != 4:
                            if not perfilprin.es_profesor():
                                form.desactivar()
                                activarselect = 1

                    else:
                        form.desactivar()
                    # if solicitud.concodigo==False:
                    #     form.edit(solicitud.concodigo)
                    # else:
                    #     form.desactivarcodigo(solicitud.concodigo)
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
                    return render(request, "adm_hdusuario/delsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'realizarencuesta':
                try:
                    data['title'] = u'Encuesta'
                    incidente = None
                    if int(request.GET.get('tipoincidente', 0)) == 2:
                        incidente = hd.HdIncidente.objects.get(pk=int(encrypt(request.GET['idincidente'])))
                        data['agente'] = incidente.h_d_incidentes.filter(estado=3, status=True).order_by('-id')[0].agente
                        data['listadopreguntas'] = HdDetEncuestas.objects.filter(encuesta__tipoincidente_id=incidente.tipoincidente.id, encuesta__activo=True, encuesta__status=True, activo=True, status=True)
                    else:
                        incidente = HdIncidente.objects.get(pk=int(encrypt(request.GET['idincidente'])))
                        data['agente'] = incidente.hddetalle_incidente_set.filter(estado=3,status=True).order_by('-id')[0].agente
                        data['listadopreguntas'] = HdDetEncuestas.objects.filter(encuesta__tipoincidente_id=incidente.tipoincidente.id,encuesta__activo=True,encuesta__status=True,activo=True,status=True)

                    data['incidente'] = incidente
                    return render(request, "adm_hdusuario/realizarencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscaractivo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    tipo = int(request.GET['idt'])
                    #if persona.usuario.is_superuser:
                    if s.__len__() == 1:
                        # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                        activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q), status=True).distinct()[:20]
                    else:
                        activo = ActivoFijo.objects.filter(
                            (Q(codigogobierno__icontains=s[0]) & Q(codigointerno__icontains=s[1])) |
                            (Q(codigogobierno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                            (Q(codigogobierno__icontains=s[0]) & Q(descripcion__icontains=s[1])) |
                            (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1])) |
                            (Q(codigointerno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                            # (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                            (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True).distinct()[:20]

                    # else:
                    #         if s.__len__() == 1:
                    #             # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                    #             activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True,responsable=persona.pk).distinct()[:20]
                    #         else:
                    #             activo = ActivoFijo.objects.filter((Q(codigogobierno__icontains=s[0])& Q(codigointerno__icontains=s[1]))|
                    #                                                (Q(codigogobierno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                    #                                                (Q(codigogobierno__icontains=s[0]) & Q(descripcion__icontains=s[1])) |
                    #                                                (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1])) |
                    #                                                (Q(codigointerno__icontains=s[0]) & Q(serie__icontains=s[1])) |
                    #                                                # (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                    #                                                (Q(codigointerno__icontains=s[0]) & Q(codigogobierno__icontains=s[1]))).filter(status=True,responsable=persona.pk).distinct()[:20]

                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_reprhd()} for x in activo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Registro de incidentes'
                filtro = Q(status=True, persona_id=persona.id)
                search = request.GET.get('s', None)
                ids = request.GET.get('id', None)
                if search:
                    ss = search.split(' ')
                    if len(ss) == 1:
                        filtro &= Q(asunto__icontains=search)
                    elif len(ss) == 2:
                        filtro &= Q(Q(asunto__icontains=ss[0]), Q(asunto__icontains=ss[1]))
                    else:
                        filtro &= Q(Q(asunto__icontains=ss[0]), Q(asunto__icontains=ss[1]), Q(asunto__icontains=ss[1]))

                if ids: filtro &= Q(id=ids)

                incidentes = HdIncidente.objects.filter(filtro).exclude(tipoincidente_id=2).order_by('estado_id')

                data['s'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['incidentes'] = incidentes

                if HdDetEncuestas.objects.filter(encuesta__tipoincidente_id=2, encuesta__activo=True, encuesta__status=True, activo=True, status=True).exists():
                    data['faltantes'] = incidentes.filter(tipoincidente_id=2, estado=3, realizoencuesta=False).count()

                data['administrativo'] = persona
                data['incidentes_tic'] = hd.HdIncidente.objects.filter(filtro).order_by('estado_id')
                return render(request, "adm_hdusuario/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')


