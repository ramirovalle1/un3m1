# -*- coding: UTF-8 -*-
import datetime
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sga.commonviews import adduserdata
from sga.forms import GrupoInvestigacionForm, ParticipanteGrupoInvestigacionForm, TematicaGrupoInvestigacionForm
from sga.funciones import log, generar_nombre
from sga.models import GrupoInvestigacion, Tematica, LineaInvestigacion, Persona, ParticipanteTematica, LineasGrupoInvestigacion


def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            # if action == 'addparticipantetematica':
            #     try:
            #         participante = ParticipanteTematica()
            #         participante.participante_id = request.POST['idp']
            #         participante.tematica_id = request.POST['id']
            #         participante.save(request)
            #         return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'Ocurrio un problema al añadir participante'}))
            # if action == 'deleteparticipantetematica':
            #     try:
            #         participante = ParticipanteTematica.objects.get(pk=request.POST['id'])
            #         participante.delete()
            #         return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'Ocurrio un problema al eliminar participante'}))
            # if action == 'addtipopublicacion':
            #     try:
            #         f = TipoPublicacionGrupoInvestigacionForm(request.POST)
            #         if f.is_valid():
            #             if not TipoPublicacionGrupo.objects.filter(tipo=f.cleaned_data['tipo'], grupo_id=request.POST['id']).exists():
            #                 tipopublicacion= TipoPublicacionGrupo()
            #                 tipopublicacion.tipo = f.cleaned_data['tipo']
            #                 tipopublicacion.grupo_id = request.POST['id']
            #                 tipopublicacion.save(request)
            #                 log(u"Adicione Tipo de Publicación : %s" % tipopublicacion, request, "add")
            #                 return HttpResponse(json.dumps({'result':'ok'}), content_type="application/json")
            #             else:
            #                 return HttpResponse(json.dumps({'result': 'bad', 'mensaje':u"El tipo de publicación ya existe"}), content_type="application/json")
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return HttpResponse(json.dumps({'result':'bad', 'mensaje':u'Ocurrio un problema al añadir tipo de publicación'}))
            # if action == 'deletetipopublicacion':
            #     try:
            #         tipopublicacion= TipoPublicacionGrupo.objects.get(pk=request.POST['id'])
            #         tipopublicacion.delete()
            #         log(u"Elimino Tipo de Publicación: %s" % tipopublicacion, request, "delete")
            #         return HttpResponse(json.dumps({'result':'ok'}), content_type="application/json")
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return HttpResponse(json.dumps({'result':'bad', 'mensaje':u'Ocurrio un problema al eliminar el tipo de publicación'}))
            #
            # if action == 'addlinea':
            #     try:
            #         f = SublineaGrupoInvestigacionForm(request.POST)
            #         if f.is_valid():
            #             if not Sublineas_GrupoInvestigacion.objects.filter(sublinea=f.cleaned_data['sublinea'], grupoinvestigacion_id=request.POST['grupo']).exists():
            #                 sublinea= Sublineas_GrupoInvestigacion()
            #                 sublinea.sublinea = f.cleaned_data['sublinea']
            #                 sublinea.grupoinvestigacion_id = request.POST['grupo']
            #                 sublinea.save(request)
            #                 log(u"Adiciono Sublinea de Investigación : %s" % sublinea, request, "add")
            #                 return HttpResponse(json.dumps({'result':'ok'}), content_type="application/json")
            #             else:
            #                 return HttpResponse(json.dumps({'result': 'bad', 'mensaje':u"Ya se ha Ingresado esta Sublinea de Investigación"}), content_type="application/json")
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return HttpResponse(json.dumps({'result':'bad', 'mensaje':'Ocurrio un problema al añadir Lina de Ivestigación al Grupo'}))
            # if action == 'deletelinea':
            #     try:
            #         linea = Sublineas_GrupoInvestigacion.objects.get(pk=request.POST['id'])
            #         linea.delete()
            #         log(u"Elimino Sublina de Investigación : %s" % linea, request, "delete")
            #         return HttpResponse(json.dumps({'result':'ok'}), content_type="application/json")
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return HttpResponse(json.dumps({'result':'bad', 'mensaje':'Ocurrio un problema al eliminar Lina de Ivestigación al Grupo'}))
            if action == 'sublineas':
                try:
                    linea = LineaInvestigacion.objects.get(pk=request.POST['id'])
                    sublineas = linea.sublineainvestigacion_set.filter(status=True)
                    options = '<option value="" selected="selected">---------</option>'
                    for sublinea in sublineas:
                        options+= '<option value="%s">%s</option>' % (sublinea.id, sublinea.nombre)

                    return JsonResponse({'result': 'ok', 'sublineas': options})
                except Exception as ex:
                    return JsonResponse({'result': 'bad'})

            if action == 'addgrupo' or action == 'editgrupo':
                try:
                    f = GrupoInvestigacionForm(request.POST)
                    if f.is_valid():
                        if action =='addgrupo':
                            grupo = GrupoInvestigacion()
                        else:
                            grupo = GrupoInvestigacion.objects.get(pk=request.POST['id'])
                        grupo.nombre = f.cleaned_data['nombre']
                        grupo.director = f.cleaned_data['director']
                        grupo.codirector = f.cleaned_data['codirector']
                        grupo.resolucion = f.cleaned_data['resolucion']
                        grupo.fecharesolucion = f.cleaned_data['fecharesolucion']
                        grupo.fechapresentacion = f.cleaned_data['fechapresentacion']
                        grupo.observacion = f.cleaned_data['observacion']
                        grupo.descripcion = f.cleaned_data['descripcion']
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("informe_resolucion_", newfile._name)
                            grupo.informeresolucion = newfile
                        grupo.save(request)
                        if action == 'addgrupo':
                            for linea in f.cleaned_data['lineas']:
                                lin = LineasGrupoInvestigacion(linea=linea, grupo=grupo)
                                lin.save(request)
                            log(u"Adiciono Grupo Investigación : %s" % grupo, request, "add")
                        else:
                            grupo.lineasgrupoinvestigacion_set.filter(grupo= grupo).exclude()
                            log(u"Edito Grupo Investigación : %s" % grupo, request, "edit")
                        return JsonResponse({'result':'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje':u"Error al guardar datos."})
            if action == 'deletegrupo':
                try:
                    grupo = GrupoInvestigacion.objects.get(pk=request.POST['id'])
                    # if not grupo.tiene_detalle():
                    grupo.status= False
                    grupo.save(request)
                    log(u"Elimino Grupo Investigación : %s" % grupo, request, "delete")
                    return JsonResponse({'result': 'ok'})
                    # else:
                    #     return HttpResponse(json.dumps({'result': 'bad', 'mensaje':u"No se puede eliminar, debido que existe un detalle"}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result':'bad', 'mensaje':u"Error al eliminar los datos"})
            # if action == 'deletecodirector':
            #     try:
            #         grupo = GrupoInvestigacion.objects.get(pk=request.POST['id'])
            #         grupo.codirector = None
            #         grupo.save(request)
            #         log(u"Elimino CoDirector del Grupo Investigación : %s" % grupo, request, "delete")
            #         return HttpResponse(json.dumps({'result':'ok'}), content_type="application/json")
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return HttpResponse(json.dumps({'result':'bad', 'mensaje':u"Error al eliminar los datos"}), content_type="application/json")
            if action == 'addtematica' or action == 'edittematica':
                try:
                    f = TematicaGrupoInvestigacionForm(request.POST)
                    # if f.is_valid():
                    if action == 'addtematica':
                        tematica = Tematica()
                        tematica.grupo_id = request.POST['id']
                    else:
                        tematica= Tematica.objects.get(pk=request.POST['id'])
                    tematica.tema = request.POST['tema']
                    tematica.tipopublicacion_id = request.POST['tipopublicacion']
                    tematica.sublinea_id = request.POST['sublinea']
                    tematica.save(request)
                    if action == 'addtematica':
                        log(u"Adiciono Tematica : %s" % tematica, request, "add")
                    else:
                        log(u"Edito Tematica : %s" % tematica, request, "edit")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result':'bad', 'mensaje':u"Error al guardar los datos"})
            if action == 'deletetematica':
                try:
                    tematica = Tematica.objects.get(pk=request.POST['id'])
                    tematica.status = False
                    tematica.save(request)
                    log(u"Elimino Tematica : %s" % tematica, request, "delete")
                    return JsonResponse({'result':'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result':'bad', 'mensaje':u"Error al eliminar los datos"})

            if action == 'addparticipante' or action == 'editparticipante':
                try:
                    f = ParticipanteGrupoInvestigacionForm(request.POST)
                    idpersona = int(request.POST['persona'])
                    if action == 'addparticipante':
                        participante = ParticipanteTematica()
                        participante.tematica_id = request.POST['id']
                    else:
                        participante = ParticipanteTematica.objects.get(pk=request.POST['id'])

                    if idpersona != 0:
                        # if ParticipanteGrupoInvestigacion.objects.filter(persona_id=idpersona, grupoinvestigacion_id=request.POST['id']).exists():
                        #     return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"}), content_type="application/json")
                        participante.persona_id = request.POST['persona']
                        participante.tipo = 1
                    else:
                        # if ParticipanteGrupoInvestigacion.objects.filter(cedula= request.POST['cedula']).exists() and action =='addparticipante':
                        #     return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"}), content_type="application/json")
                        participante.nombre = request.POST['nombre']
                        participante.apellido = request.POST['apellido']
                        participante.cedula = request.POST['cedula']
                        participante.tipo = 2
                    participante.save(request)
                    if action == 'addparticipante':
                        log(u"Añadio participante : %s" % participante, request, "add")
                    else:
                        log(u"Edito participante : %s" % participante, request, "edit")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result':'bad', 'mensaje':u"Error al guardar los datos"})
            #
            # if action == 'deleteparticipante':
            #     try:
            #         participante = ParticipanteGrupoInvestigacion.objects.get(pk=request.POST['id'])
            #         participante.delete()
            #         log(u"Elimino Participante : %s" % participante, request, "delete")
            #         return HttpResponse(json.dumps({'result':'ok'}), content_type="application/json")
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return HttpResponse(json.dumps({'result':'bad', 'mensaje':u"Error al eliminar los datos"}), content_type="application/json")
            if action == 'enviargrupo':
                try:
                    grupo = GrupoInvestigacion.objects.get(pk=request.POST['id'])
                    grupo.estado = 3
                    grupo.fechapresentacion = datetime.now()
                    grupo.save(request)
                    log(u"Envio Grupo de Investigación : %s" % grupo, request, "send")
                    return JsonResponse({'result':'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u"Error al enviar Grupo de Investigación"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'addgrupo':
                try:
                    data['title'] = u"Añadir Grupo de Investigación"
                    form = GrupoInvestigacionForm()
                    form.profesor_nombramiento()
                    data['form'] = form
                    return render(request, "pro_grupo_investigacion/addgrupo.html", data)
                except Exception as ex:
                    pass
            elif action == 'editgrupo':
                try:
                    data['title'] = u"Editar Grupo de Investigación"
                    data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    form = GrupoInvestigacionForm(initial={
                        'nombre': grupo.nombre,
                        'director' : grupo.director,
                        'codirector': grupo.codirector
                    })
                    form.profesor_nombramiento()
                    data['form'] = form
                    return render(request, "pro_grupo_investigacion/editgrupo.html", data)
                except Exception as ex:
                    pass
            elif action == 'deletegrupo':
                try:
                    data['title'] = u'Eliminar Grupo de Investigación'
                    data['grupo'] = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    return render(request, "pro_grupo_investigacion/deletegrupo.html", data)
                except Exception as ex:
                    pass
            # elif action =='deletecodirector':
            #     try:
            #         data['title'] = u'Eliminar CoDirector del Grupo de Investigación'
            #         data['grupo'] = GrupoInvestigacion.objects.get(pk=request.GET['id'])
            #         return render(request, "pro_grupo_investigacion/deletecodirector.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'detailgrupo':
                try:
                    data['title'] =u"Detalle Grupo de Investigación"
                    data['grupo'] = grupo =GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['tematicas'] = grupo.tematica_set.filter(status=True).order_by('tema')

                    # data['sublineas'] = grupo.sublineas_grupoinvestigacion_set.filter(status=True).order_by('sublinea__lineainvestigacion')
                    # data['participantes'] = grupo.participantegrupoinvestigacion_set.filter(status=True)
                    # data['tipospublicaciones'] = grupo.tipopublicaciongrupo_set.filter(status=True)
                    return render(request, "pro_grupo_investigacion/viewtematica.html", data)
                except Exception as ex:
                    pass
            # elif action == 'addlinea':
            #     try:
            #         data['title'] = u"Añadir Linea de Investigación"
            #         data['form'] = SublineaGrupoInvestigacionForm()
            #         data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=request.GET['id'])
            #         return render(request, "pro_grupo_investigacion/addlinea.html", data)
            #     except Exception as ex:
            #         pass
            # elif action =='deletelinea':
            #     try:
            #         data['title'] = u"Eliminar Línea de Investigación"
            #         data['linea'] = linea =Sublineas_GrupoInvestigacion.objects.get(pk=request.GET['id'])
            #         data['grupo'] = linea.grupoinvestigacion
            #         return render(request, "pro_grupo_investigacion/deletelinea.html", data)
            #     except Exception as ex:
            #         pass
            # elif action == 'addtipopublicacion':
            #     try:
            #         data['title'] = u"Añadir Tipo de Publicación"
            #         data['form'] = TipoPublicacionGrupoInvestigacionForm()
            #         data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=request.GET['id'])
            #         return render(request, "pro_grupo_investigacion/addtipopublicacion.html", data)
            #     except Exception as ex:
            #         pass
            # elif action == 'deletetipopublicacion':
            #     try:
            #         data['title'] = u"Eliminar Tipo de Publición"
            #         data['tipo'] = tipo = TipoPublicacionGrupo.objects.get(pk=request.GET['id'])
            #         data['grupo'] = tipo.grupo
            #         return render(request, "pro_grupo_investigacion/deletetipopublicacion.html", data)
            #     except Exception as ex:
            #         pass
            elif action == 'addtematica':
                try:
                    data['title'] = u"Añadir línea de investigación"
                    data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['form'] = TematicaGrupoInvestigacionForm()
                    return render(request, "pro_grupo_investigacion/addtematica.html", data)
                except Exception as ex:
                    pass
            elif action == 'edittematica':
                try:
                    data['title'] = u"Editar línea de investigación"
                    data['tematica']= tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    form = TematicaGrupoInvestigacionForm(initial={'tema': tematica.tema, 'tipopublicacion': tematica.tipopublicacion})
                    data['form'] = form
                    return render(request, "pro_grupo_investigacion/edittematica.html", data)
                except Exception as ex:
                    pass
            elif action =='deletetematica':
                try:
                    data['title'] = u"Eliminar Tematica de Investigación"
                    data['tematica'] = tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    return render(request, "pro_grupo_investigacion/deletetematica.html", data)
                except Exception as ex:
                    pass
            elif action =='detailtematica':
                try:
                    data['title'] = u"Detalle Tematica"
                    data['tematica'] = tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    data['participantes'] = tematica.participantetematica_set.all()
                    return render(request, "pro_grupo_investigacion/detailtematica.html", data)
                except Exception as ex:
                    pass
            # elif action == 'addparticipantetematica':
            #     try:
            #         data['title'] = u"Participantes Tematica de Investigación"
            #         data['tematica'] = tematica = Tematica.objects.get(pk=request.GET['id'])
            #         lista = tematica.participantetematica_set.filter(status=True)
            #         if lista.count() > 0:
            #             data['participantes'] = tematica.participantetematica_set.filter(status=True).exclude(lista)
            #         else:
            #             data['participantes'] = tematica.participantetematica_set.filter(status=True)
            #         return render(request, "pro_grupo_investigacion/listaparticipante.html", data)
            #     except Exception as ex:
            #         pass
            # elif action == 'deleteparticipantetematica':
            #     try:
            #         data['title'] = u"Eliminar participante"
            #         data['participante'] = participante = ParticipanteTematica.objects.get(pk=request.GET['id'])
            #         data['tematica'] = participante.tematica
            #         return render(request, "pro_grupo_investigacion/deleteparticipantetematica.html", data)
            #     except Exception as ex:
            #         pass
            elif action =='addparticipante':
                try:
                    data['title'] = u"Añadir Participante de Investigación"
                    data['tematica'] = tematica= Tematica.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    form= ParticipanteGrupoInvestigacionForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "pro_grupo_investigacion/addparticipante.html", data)
                except Exception as ex:
                    pass
            # elif action =='editparticipante':
            #     try:
            #         data['title'] = u"Editar Participante de Investigación"
            #         data['participante'] = participante = ParticipanteGrupoInvestigacion.objects.get(pk=request.GET['id'])
            #         data['grupo'] = participante.grupoinvestigacion
            #         form = ParticipanteGrupoInvestigacionForm(initial={
            #             'cedula':participante.cedula,
            #             'nombre': participante.nombre,
            #             'apellido': participante.apellido
            #         })
            #         form.editar()
            #         data['form'] = form
            #         return render(request, "pro_grupo_investigacion/editparticipante.html", data)
            #     except Exception as ex:
            #         pass
            # elif action =='deleteparticipante':
            #     try:
            #         data['title'] = u"Eliminar Participante de Investigación"
            #         data['participante'] = participante =ParticipanteGrupoInvestigacion.objects.get(pk=request.GET['id'])
            #         data['grupo'] = participante.grupoinvestigacion
            #         return render(request, "pro_grupo_investigacion/deleteparticipante.html", data)
            #     except Exception as ex:
            #         pass
            elif action == 'enviargrupo':
                try:
                    data['title'] = u"Enviar Grupo de Investigacion"
                    data['grupo'] = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['mensaje'] = u"Una vez enviado no podra hacer modificaciones hasta obtener una respuesta, Grupo de Investigación: "
                    return render(request, "pro_grupo_investigacion/enviargrupo.html", data)
                except Exception as ex:
                    pass
            #
            elif action == 'busqueda':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s)== 1:
                        personas = Persona.objects.filter(Q(cedula__contains=q) | Q(nombres__contains=q) | Q(apellido1__contains=q) | Q(apellido2__contains=q)).distinct()[:20]
                    else:
                        personas = Persona.objects.filter(Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])).distinct()[:20]

                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(), "cedula": x.cedula, "nombre":x.nombres, "apellido": x.apellido1 +" "+ x.apellido2} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad'})
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u"Grupo de Investigación"
            data['grupos'] = GrupoInvestigacion.objects.filter(status=True).order_by('id')
            return render(request, "pro_grupo_investigacion/viewgrupo.html", data)
