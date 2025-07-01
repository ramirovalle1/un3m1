# -*- coding: UTF-8 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from django.db.models import Q
from sga.forms import ParticipanteGrupoInvestigacionForm
from sga.funciones import log, variable_valor, MiPaginador
from sga.models import SolicitudGrupoInvestigacion, Persona, SolicitudParticipanteGrupoInvestigacion, \
    SolicitudTematicaGrupoInvestigacion, SolicitudLineasGrupoInvestigacion, SolicitudLineasTematica, \
    SolicitudParticipanteTematica, SolicitudDetalleGrupoInvestigacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    adduserdata(request, data)
    solicitado_detalle=1
    aprobado_detalle = 2
    rechazado_detalle = 3
    if request.method == 'POST':
        action = request.POST['action']
        #GRUPO
        if action == 'addgrupo':
            try:
                form = SolicitudGrupoInvestigacionForm(request.POST)
                if form.is_valid():
                    solicitud=SolicitudGrupoInvestigacion(nombre=form.cleaned_data['nombre'],
                                                          descripcion=form.cleaned_data['descripcion'],
                                                          director_id=form.cleaned_data['director'],
                                                          codirector_id=form.cleaned_data['codirector'] if form.cleaned_data['codirector']>0 else None,
                                                          observacion=form.cleaned_data['observacion'],
                                                          estado=variable_valor('CREADO_GRUPO_INVESTIGACION'))
                    solicitud.save(request)
                    for linea in form.cleaned_data['lineas']:
                        line = SolicitudLineasGrupoInvestigacion(linea=linea, grupo=solicitud)
                        line.save(request)
                    log(u'Adiciono una solicitud de grupo de investigación   : %s - [%s]' % (solicitud,solicitud.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editgrupo':
            try:
                form = SolicitudGrupoInvestigacionForm(request.POST)
                if form.is_valid():
                    solicitud = SolicitudGrupoInvestigacion.objects.get(pk=int(request.POST['id']))
                    solicitud.nombre = form.cleaned_data['nombre']
                    solicitud.descripcion = form.cleaned_data['descripcion']
                    solicitud.director_id = form.cleaned_data['director']
                    solicitud.codirector_id = form.cleaned_data['codirector'] if  form.cleaned_data['codirector']>0 else None
                    solicitud.observacion = form.cleaned_data['observacion']
                    solicitud.save(request)
                    eliminar = SolicitudLineasGrupoInvestigacion.objects.filter(grupo=solicitud, solicitudlineastematica__linea__isnull=True).exclude(linea__in=form.cleaned_data['lineas'])
                    for eliminando in eliminar:
                            log(u'Elimino una linea de grupo de investigacion  : %s - [%s]' % (eliminando, eliminando.id),request, "del")
                    eliminar.delete()
                    for linea in form.cleaned_data['lineas']:
                        if not SolicitudLineasGrupoInvestigacion.objects.filter(linea=linea, grupo=solicitud).exists():
                            line = SolicitudLineasGrupoInvestigacion(linea=linea, grupo=solicitud)
                            line.save(request)
                    log(u'Edito una solicitud de grupo de investigacion  : %s - [%s]' % (solicitud,solicitud.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delgrupo':
            try:
                solicitud = SolicitudGrupoInvestigacion.objects.get(pk=int(request.POST['id']))
                if solicitud.solicitudtematicagrupoinvestigacion_set.all():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede eliminar, este grupo cuenta con temáticas asignadas."})
                log(u'Elimino una solicitud de grupo de investigacion  : %s - [%s]' % (solicitud,solicitud.id), request, "del")
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'solicitar':
            try:
                solicitud = SolicitudGrupoInvestigacion.objects.get(pk=int(request.POST['id']))
                solicitud.estado = variable_valor('SOLICITADO_GRUPO_INVESTIGACION')
                solicitud.save()
                detalle=SolicitudDetalleGrupoInvestigacion(cabecera=solicitud,
                                                           aprueba=solicitud.director.persona,
                                                           fechaaprobacion=datetime.now(),
                                                           observacion="SOLICITUD DE APROBACIÓN",
                                                           estado=solicitado_detalle)
                detalle.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"No puede solicitar grupo de investigación."})

        #PARTICIPANTE
        elif action == 'addparticipante':
            try:
                form = ParticipanteGrupoInvestigacionForm(request.POST)
                if form.is_valid():
                    idpersona = int(request.POST['persona'])
                    participante = SolicitudParticipanteGrupoInvestigacion()
                    participante.rol_id = int(request.POST['rol'])
                    participante.grupo_id = request.POST['id']
                    if not idpersona != 0:
                        if SolicitudParticipanteGrupoInvestigacion.objects.filter(cedula=request.POST['cedula']).exists():
                            return JsonResponse({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"})
                        participante.nombre = request.POST['nombre']
                        participante.apellido = request.POST['apellido']
                        participante.cedula = request.POST['cedula']
                        participante.correo = request.POST['correo']
                        participante.institucion = request.POST['institucion'].upper()
                        participante.formacion = request.POST['formacion'].upper()
                        participante.tipo = 2
                    else:
                        if SolicitudParticipanteGrupoInvestigacion.objects.filter(persona_id=idpersona,grupo_id=int(request.POST['id']),status=True).exists():
                            return JsonResponse({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"})
                        participante.persona_id = idpersona
                        participante.tipo = 1
                    participante.save(request)
                    log(u"Adiciono participante en solicitud grupo de investigacion : %s - [%s]" % (participante,participante.id), request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editparticipante':
            try:
                form = ParticipanteGrupoInvestigacionForm(request.POST)
                if form.is_valid():
                    idpersona = int(request.POST['persona'])
                    participante = SolicitudParticipanteGrupoInvestigacion.objects.get(pk=int(request.POST['id']))
                    if not idpersona != 0:
                        if SolicitudParticipanteGrupoInvestigacion.objects.filter((Q(cedula=request.POST['cedula']) | Q(persona__cedula=request.POST['cedula'])),Q(grupo_id=int(request.POST['id'])), status=True).exists():
                            return JsonResponse({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"})
                        participante.nombre = request.POST['nombre']
                        participante.apellido = request.POST['apellido']
                        participante.cedula = request.POST['cedula']
                        participante.correo = request.POST['correo']
                        participante.institucion = request.POST['institucion'].upper()
                        participante.formacion = request.POST['formacion'].upper()
                        participante.persona = None
                        participante.tipo = 2
                    else:
                        if SolicitudParticipanteGrupoInvestigacion.objects.filter(persona_id=idpersona,grupo_id=int(request.POST['id']),status=True).exclude(persona=participante.persona).exists():
                            return JsonResponse({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"})
                        participante.persona_id = int(request.POST['persona'])
                        participante.rol_id = int(request.POST['rol'])
                        participante.tipo = 1
                        participante.nombre = None
                        participante.apellido = None
                        participante.cedula = None
                        participante.correo = None
                        participante.institucion = None
                        participante.formacion = None
                    participante.save(request)
                    log(u"Edito participante en solicitud grupo de investigacion : %s - [%s]" % (participante,participante.id), request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delparticipante':
            try:
                participante = SolicitudParticipanteGrupoInvestigacion.objects.get(pk=request.POST['id'])
                if participante.solicitudparticipantetematica_set.all():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el participante tiene tematicas asignado."})
                log(u"Elimino participante en solicitud grupo de investigacion : %s - [%s]" % (participante, participante.id), request, "del")
                participante.delete()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':'bad', 'mensaje':u"Error al eliminar los datos"})

        #TEMATICA
        elif action == 'addtematica':
            try:
                form = SolicitudTematicaGrupoInvestigacionForm(request.POST)
                if form.is_valid():
                    tematica = SolicitudTematicaGrupoInvestigacion()
                    tematica.grupo_id = request.POST['id']
                    tematica.tema = form.cleaned_data['tema']
                    tematica.tipopublicacion = form.cleaned_data['tipopublicacion']
                    tematica.save(request)
                    for linea in form.cleaned_data['lineas']:
                        line = SolicitudLineasTematica(linea=linea, tematica=tematica)
                        line.save(request)
                        log(u"Adiciono linea en tematica de solicitud grupo de investigacion : %s - [%s]" % (linea, linea.id), request, "add")
                    log(u"Adiciono tematica en solicitud grupo de investigacion : %s - [%s]" % (tematica,tematica.id), request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittematica':
            try:
                form = SolicitudTematicaGrupoInvestigacionForm(request.POST)
                if form.is_valid():
                    tematica = SolicitudTematicaGrupoInvestigacion.objects.get(pk=request.POST['id'])
                    tematica.tema = form.cleaned_data['tema']
                    tematica.tipopublicacion = form.cleaned_data['tipopublicacion']
                    tematica.save(request)
                    eliminarlineas = SolicitudLineasTematica.objects.filter(tematica=tematica).exclude(linea__in=form.cleaned_data['lineas'])
                    for eliminando in eliminarlineas:
                        log(u"Elimino linea en tematica de solicitud grupo de investigacion: %s - [%s]" % (eliminando, eliminando.id), request, "del")
                    eliminarlineas.delete()
                    for linea in form.cleaned_data['lineas']:
                        if not SolicitudLineasTematica.objects.filter(linea=linea, tematica=tematica).exists():
                            line = SolicitudLineasTematica(linea=linea, tematica=tematica)
                            line.save(request)
                    log(u"Edito tematica en solicitud grupo de investigacion : %s - [%s]" % (tematica,tematica.id), request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deltematica':
            try:
                tematica = SolicitudTematicaGrupoInvestigacion.objects.get(pk=request.POST['id'])
                log(u"Elimino solicitud tematica de grupo de investigacion : %s - [%s]" % (tematica, tematica.id), request, "del")
                tematica.delete()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':'bad', 'mensaje':u"Error al eliminar los datos"})

        #PARTICIPANTE TEMATICA
        elif action == 'addparticipantetematica':
            try:
                participante = SolicitudParticipanteTematica()
                participante.participante_id = request.POST['idp']
                participante.tematica_id = request.POST['id']
                participante.save(request)
                log(u"Adicionó Participante Tematica de grupo de investigacion: %s - [%s]" % (participante,participante.id), request, "add")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrió un problema al añadir participante'})

        elif action == 'delparticipantetematica':
            try:
                participante = SolicitudParticipanteTematica.objects.get(pk=request.POST['id'])
                log(u"Elimino Participante en tematica grupo de investigacion %s - [%s]" % (participante, participante.id), request, "del")
                participante.delete()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrió un problema al eliminar participante'})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            #GRUPO
            if action == 'addgrupo':
                try:
                    data['title'] = u'Adicionar grupo de investigación'
                    data['form'] = SolicitudGrupoInvestigacionForm()
                    return render(request, "pro_solicitudgrupoinvestigacion/addgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editgrupo':
                try:
                    data['title'] = u'Editar grupo de investigación'
                    data['grupo'] = solicitud=SolicitudGrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    form = SolicitudGrupoInvestigacionForm(initial={'nombre':solicitud.nombre,
                                                                    'observacion':solicitud.observacion,
                                                                    'director':solicitud.director.id,
                                                                    'codirector': solicitud.codirector.id if solicitud.codirector else 0,
                                                                    'descripcion': solicitud.descripcion})
                    form.editar(solicitud.director,solicitud.codirector)
                    data['form'] = form
                    data['lineas'] = solicitud.solicitudlineasgrupoinvestigacion_set.all()
                    return render(request, "pro_solicitudgrupoinvestigacion/editgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delgrupo':
                try:
                    data['title'] = u'Eliminar grupo de investigación'
                    data['grupo'] = SolicitudGrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "pro_solicitudgrupoinvestigacion/delgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleavance':
                try:
                    data = {}
                    cabecera = SolicitudGrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    data['cabecerasolicitud'] = cabecera
                    data['detallesolicitud'] = cabecera.solicituddetallegrupoinvestigacion_set.all()
                    data['creado'] = variable_valor('CREADO_GRUPO_INVESTIGACION')
                    data['solicitado'] = variable_valor('SOLICITADO_GRUPO_INVESTIGACION')
                    data['aprobado'] = variable_valor('APROBADO_GRUPO_INVESTIGACION')
                    template = get_template("adm_solicitudaprobacioninvestigacion/detalleavance.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detallegrupo':
                try:
                    data['grupo'] = SolicitudGrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    template = get_template("pro_solicitudgrupoinvestigacion/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # PARTICIPANTE
            elif action == 'busqueda':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        personas = Persona.objects.filter(Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1]) & Q(tipopersona=1))[:20]
                    else:
                        personas = Persona.objects.filter((Q(cedula__contains=s[0]) | Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q(apellido2__contains=s[0]) | Q(nombres__contains=s[0])) & Q(tipopersona=1))[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(), "cedula": x.cedula, "nombre": x.nombres,"apellido": x.apellido1 + " " + x.apellido2, "correo": x.email,"formacion": x.titulacion_principal_senescyt()} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad'})

            elif action == 'addparticipante':
                try:
                    data['title'] = u"Adicionar participante"
                    data['grupo'] = SolicitudGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    form = ParticipanteGrupoInvestigacionForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "pro_solicitudgrupoinvestigacion/addparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'delparticipante':
                try:
                    data['title'] = u'Eliminar Participante'
                    data['participante'] = participante =SolicitudParticipanteGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['grupo']= participante.grupo
                    return render(request, "pro_solicitudgrupoinvestigacion/delparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editparticipante':
                try:
                    data['title'] = u"Editar participante"
                    data['participante'] = participante = SolicitudParticipanteGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['grupo'] = participante.grupo
                    form = ParticipanteGrupoInvestigacionForm(initial={
                            'cedula': participante.cedula if participante.tipo == 2 else participante.persona.cedula,
                            'nombre': participante.nombre if participante.tipo == 2 else  participante.persona.nombres,
                            'apellido': participante.apellido if participante.tipo == 2 else participante.persona.apellido1 + " " + participante.persona.apellido2,
                            'correo': participante.correo if participante.tipo == 2 else participante.persona.email,
                            'institucion': participante.institucion if participante.tipo == 2 else  'UNEMI',
                            'formacion': participante.formacion if participante.tipo == 2 else participante.persona.titulacion_principal_senescyt(),
                            'rol': participante.rol if participante.tipo == 2 else participante.rol,
                            'participante': participante.tipo})
                    if participante.tipo == 2:
                        form.deshabilitar_busqueda()
                    else:
                        form.adicionar()
                    data['form'] = form
                    return render(request, "pro_solicitudgrupoinvestigacion/editparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'participante':
                try:
                    data['title'] = u"Participantes"
                    data['grupo'] = grupo = SolicitudGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['participantes'] = grupo.solicitudparticipantegrupoinvestigacion_set.filter(status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres','apellido','nombre')
                    return render(request, "pro_solicitudgrupoinvestigacion/viewparticipante.html", data)
                except Exception as ex:
                    pass

            #TEMATICA
            elif action == 'addtematica':
                try:
                    data['title'] = u"Adicionar línea de investigación"
                    data['grupo'] = grupo = SolicitudGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    form = SolicitudTematicaGrupoInvestigacionForm()
                    form.cargar_lineas(grupo)
                    data['form'] = form
                    return render(request, "pro_solicitudgrupoinvestigacion/addtematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittematica':
                try:
                    data['title'] = u"Editar línea de investigación"
                    data['tematica'] = tematica = SolicitudTematicaGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    form = SolicitudTematicaGrupoInvestigacionForm(initial={'tema': tematica.tema, 'tipopublicacion': tematica.tipopublicacion})
                    form.cargar_lineas(tematica.grupo)
                    data['form'] = form
                    data['lineas'] = tematica.solicitudlineastematica_set.all()
                    return render(request, "pro_solicitudgrupoinvestigacion/edittematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'deltematica':
                try:
                    data['title'] = u"Eliminar Tematica"
                    data['tematica'] = tematica = SolicitudTematicaGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    return render(request, "pro_solicitudgrupoinvestigacion/deltematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'tematica':
                try:
                    data['title'] = u"línea de investigación de Grupo de Investigación"
                    data['tematicas'] = SolicitudTematicaGrupoInvestigacion.objects.filter(grupo_id=int(request.GET['id']), status=True)
                    data['grupo'] = SolicitudGrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "pro_solicitudgrupoinvestigacion/viewtematicas.html", data)
                except Exception as ex:
                    pass

            #PARTICIPANTE EN TEMATICA
            elif action == 'addparticipantetematica':
                try:
                    data['title'] = u"Participantes Tematica de Investigación"
                    data['tematica'] = tematica = SolicitudTematicaGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    lista = tematica.solicitudparticipantetematica_set.values_list('participante').filter(status=True)
                    if lista.count() > 0:
                        data['participantes'] = tematica.grupo.solicitudparticipantegrupoinvestigacion_set.filter(status=True).exclude(pk__in=lista)
                    else:
                        data['participantes'] = tematica.grupo.solicitudparticipantegrupoinvestigacion_set.filter(status=True)
                    return render(request, "pro_solicitudgrupoinvestigacion/addparticipantetematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delparticipantetematica':
                try:
                    data['title'] = u"Eliminar participante"
                    data['participante'] = participante = SolicitudParticipanteTematica.objects.get(pk=request.GET['id'])
                    data['tematica'] = participante.tematica
                    return render(request, "pro_solicitudgrupoinvestigacion/delparticipantetematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'participantetematica':
                try:
                    data['title'] = u"Participantes en línea de investigación"
                    data['tematica'] = tematica = SolicitudTematicaGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['grupo'] = tematica.grupo
                    data['participantes'] = tematica.solicitudparticipantetematica_set.filter(status=True).order_by('participante__persona__apellido1', 'participante__persona__apellido2', 'participante__persona__nombres','participante__apellido','participante__nombre')
                    return render(request, "pro_solicitudgrupoinvestigacion/participantetematica.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes de grupo investigación'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    grupos = SolicitudGrupoInvestigacion.objects.filter((Q(codirector__persona__nombres__icontains=search) |
                                                                    Q(codirector__persona__apellido1__icontains=search) |
                                                                    Q(codirector__persona__apellido2__icontains=search) |
                                                                    Q(codirector__persona__cedula__icontains=search) |
                                                                    Q(codirector__persona__pasaporte__icontains=search)|
                                                                    Q(director__persona__nombres__icontains=search) |
                                                                    Q(director__persona__apellido1__icontains=search) |
                                                                    Q(director__persona__apellido2__icontains=search) |
                                                                    Q(director__persona__cedula__icontains=search) |
                                                                    Q(director__persona__pasaporte__icontains=search) |
                                                                    Q(nombre__icontains=search)) & Q(status=True)& Q(director=profesor)).distinct().\
                                                                    order_by('nombre','director__persona__apellido1', 'director__persona__apellido2','director__persona__nombres')
                else:
                    grupos = SolicitudGrupoInvestigacion.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]) & Q(status=True)& Q(director=profesor)).distinct().order_by('nombre')
            else:
                grupos = SolicitudGrupoInvestigacion.objects.filter(status=True , director=profesor).order_by('-fecha_creacion')
            paging = MiPaginador(grupos, 20)
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
            data['grupos'] = page.object_list
            data['creado'] = variable_valor('CREADO_GRUPO_INVESTIGACION')
            data['pendiente'] = variable_valor('PENDIENTE_GRUPO_INVESTIGACION')
            data['solicitado'] = variable_valor('SOLICITADO_GRUPO_INVESTIGACION')
            data['aprobado'] = variable_valor('APROBADO_GRUPO_INVESTIGACION')
            return render(request, "pro_solicitudgrupoinvestigacion/viewgrupo.html", data)
