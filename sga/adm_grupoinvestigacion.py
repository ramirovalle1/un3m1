# -*- coding: UTF-8 -*-
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.contrib.auth.decorators import login_required
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import GrupoInvestigacionForm, TematicaGrupoInvestigacionForm, \
    ParticipanteGrupoInvestigacionForm, ParticipanteRolForm
from sga.funciones import log, generar_nombre, MiPaginador
from sga.models import GrupoInvestigacion, Tematica, Persona, LineasGrupoInvestigacion, \
    ParticipanteGrupoInvestigacion, LineasTematica, ParticipanteTematica, ComplexivoTematica, ParticipanteRol

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addparticipantetematica':
                try:
                    participante = ParticipanteTematica()
                    participante.participante_id = request.POST['idp']
                    participante.tematica_id = request.POST['id']
                    participante.save(request)
                    log(u"Adicionó Participante a lalínea de investigación : %s" % participante, request, "add")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrió un problema al añadir participante'})

            elif action == 'deleteparticipantetematica':
                try:
                    participante = ParticipanteTematica.objects.get(pk=request.POST['id'])
                    if ComplexivoTematica.objects.filter(status=True, tutor = participante).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u"El participante fue designado acompañante de una tematica"})
                    participante.status = False
                    participante.save(request)
                    log(u"Elimino Participante a la línea de investigación : %s" % participante, request, "delete")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrió un problema al eliminar participante'})

            elif action == 'addgrupo':
                try:
                    if not 'lineas' in request.POST:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Debe selecionar al menos una línea de investigación'})
                    f = GrupoInvestigacionForm(request.POST, request.FILES)
                    if f.is_valid():
                        grupo = GrupoInvestigacion()
                        grupo.nombre = f.cleaned_data['nombre']
                        grupo.director_id = f.cleaned_data['director']
                        grupo.codirector_id = f.cleaned_data['codirector']
                        grupo.resolucion = f.cleaned_data['resolucion']
                        grupo.fecharesolucion = f.cleaned_data['fecharesolucion']
                        grupo.fechapresentacion = f.cleaned_data['fechapresentacion']
                        grupo.observacion = f.cleaned_data['observacion']
                        grupo.descripcion = f.cleaned_data['descripcion']
                        grupo.estado = 1
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("informe_resolucion_", newfile._name)
                            grupo.informeresolucion = newfile
                        grupo.save(request)

                        for lin in grupo.lineasgrupoinvestigacion_set.filter(grupo=grupo):
                            if not LineasTematica.objects.filter(linea=lin, tematica__grupo=grupo).exists():
                                lin.delete()

                        for linea in f.cleaned_data['lineas']:
                            if not LineasGrupoInvestigacion.objects.filter(linea=linea, grupo=grupo).exists():
                                lin = LineasGrupoInvestigacion(linea=linea, grupo=grupo)
                                lin.save(request)
                        log(u"Adicionó Grupo Investigación : %s" % grupo, request, "add")
                        return JsonResponse({'result':'ok'})
                    return JsonResponse({"result": "bad", 'mensaje': u"Error al guardar. Datos incorrectos"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje':u"Error al guardar datos."})

            elif action == 'editgrupo':
                try:
                    f = GrupoInvestigacionForm(request.POST, request.FILES)
                    if f.is_valid():
                        grupo = GrupoInvestigacion.objects.get(pk=request.POST['id'])
                        grupo.nombre = f.cleaned_data['nombre']
                        grupo.director_id = f.cleaned_data['director']
                        if f.cleaned_data['codirector']:
                            grupo.codirector_id = f.cleaned_data['codirector']
                        grupo.resolucion = f.cleaned_data['resolucion']
                        grupo.fecharesolucion = f.cleaned_data['fecharesolucion']
                        grupo.fechapresentacion = f.cleaned_data['fechapresentacion']
                        grupo.observacion = f.cleaned_data['observacion']
                        grupo.descripcion = f.cleaned_data['descripcion']
                        grupo.estado = 1
                        grupo.save(request)
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("informe_resolucion_", newfile._name)
                            grupo.informeresolucion = newfile
                            grupo.save(request)

                        for lin in grupo.lineasgrupoinvestigacion_set.filter(grupo=grupo):
                            if not LineasTematica.objects.filter(linea=lin, tematica__grupo=grupo).exists():
                                lin.delete()

                        for linea in f.cleaned_data['lineas']:
                            if not LineasGrupoInvestigacion.objects.filter(linea=linea, grupo=grupo).exists():
                                lin = LineasGrupoInvestigacion(linea=linea, grupo=grupo)
                                lin.save(request)
                        log(u"Editó Grupo Investigación : %s" % grupo, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje':u"Error al guardar datos."})

            elif action == 'deletegrupo':
                try:
                    grupo = GrupoInvestigacion.objects.get(pk=request.POST['id'])
                    if grupo.puede_eliminar():
                        grupo.status= False
                        grupo.save(request)
                        log(u"Eliminó Grupo Investigación : %s" % grupo, request, "delete")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje':u"Error al eliminar los datos. El grupo es usado por línea de investigación/proceso de titulación"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result':'bad', 'mensaje':u"Error al eliminar los datos"})

            elif action == 'addparticipante' or action == 'editparticipante':
                try:
                    form = ParticipanteGrupoInvestigacionForm(request.POST)
                    idpersona = int(request.POST['persona'])
                    if action == 'addparticipante':
                        participante = ParticipanteGrupoInvestigacion()
                        participante.rol_id = int(request.POST['rol'])
                        participante.grupo_id = request.POST['id']
                        if not idpersona != 0:
                            if ParticipanteGrupoInvestigacion.objects.filter(cedula=request.POST['cedula']).exists():
                                return JsonResponse({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"})
                            participante.nombre = request.POST['nombre']
                            participante.apellido = request.POST['apellido']
                            participante.cedula = request.POST['cedula']
                            participante.correo = request.POST['correo']
                            participante.institucion = request.POST['institucion'].upper()
                            participante.formacion = request.POST['formacion'].upper()
                            participante.tipo = 2
                        else:
                            if ParticipanteGrupoInvestigacion.objects.filter(persona_id=idpersona,grupo_id=int(request.POST['id']),status=True).exists():
                                return JsonResponse({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"})
                            participante.persona_id = int(request.POST['persona'])
                            participante.tipo = 1
                    else:
                        participante = ParticipanteGrupoInvestigacion.objects.get(pk=int(request.POST['id']))
                        if not idpersona != 0:
                            if ParticipanteGrupoInvestigacion.objects.filter((Q(cedula=request.POST['cedula'])|Q(persona__cedula=request.POST['cedula'])),Q(grupo_id=int(request.POST['id'])),status=True).exists():
                                return JsonResponse({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"})
                            participante.nombre = request.POST['nombre']
                            participante.apellido = request.POST['apellido']
                            participante.cedula = request.POST['cedula']
                            participante.correo = request.POST['correo']
                            participante.institucion = request.POST['institucion'].upper()
                            participante.formacion = request.POST['formacion'].upper()
                            participante.persona=None
                            participante.tipo = 2
                        else:
                            if ParticipanteGrupoInvestigacion.objects.filter(persona_id=idpersona,grupo_id=int(request.POST['id']),status=True).exclude(persona=participante.persona).exists():
                                return JsonResponse({'result': 'bad', 'mensaje': u"El participante ya se ha ingresado"})
                            participante.persona_id = int(request.POST['persona'])
                            participante.rol_id= int(request.POST['rol'])
                            participante.tipo = 1
                            participante.nombre = None
                            participante.apellido = None
                            participante.cedula = None
                            participante.correo = None
                            participante.institucion = None
                            participante.formacion = None
                    participante.save(request)
                    if action == 'addparticipante':
                        log(u"Añadió participante : %s" % participante, request, "add")
                    else:
                        log(u"Editó participante : %s - [%s]" % (participante,participante.id), request, "edit")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result':'bad', 'mensaje':u"Error al guardar los datos"})

            elif action == 'deleteparticipante':
                try:
                    participante = ParticipanteGrupoInvestigacion.objects.get(pk=request.POST['id'])
                    if not participante.asignadoatematica():
                        participante.status= False
                        participante.save(request)
                        log(u"Eliminó participante : %s" % participante, request, "delete")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje':u"Error al eliminar. El participante se encuentra en línea de investigación"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result':'bad', 'mensaje':u"Error al eliminar los datos"})

            elif action == 'addtematica' or action == 'edittematica':
                try:
                    if not 'lineas' in request.POST:
                        if action == 'addtematica':
                            return JsonResponse({'result': 'bad', 'mensaje': u'Debe selecionar al menos una línea de investigación'})
                    f = TematicaGrupoInvestigacionForm(request.POST)
                    if f.is_valid():
                        if action == 'addtematica':
                            tematica = Tematica()
                            tematica.grupo_id = request.POST['id']
                            tematica.vigente = False
                        else:
                            tematica= Tematica.objects.get(pk=request.POST['id'])
                        tematica.tema = f.cleaned_data['tema']
                        tematica.tipopublicacion = f.cleaned_data['tipopublicacion']
                        tematica.save(request)
                        tematica.lineastematica_set.all().delete()
                        for linea in f.cleaned_data['lineas']:
                            lin = LineasTematica(tematica=tematica, linea= linea)
                            lin.save(request)
                        if action == 'addtematica':
                            log(u"Adicionó línea de investigación : %s" % tematica, request, "add")
                        else:
                            log(u"Editó línea de investigación : %s" % tematica, request, "edit")
                        return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result':'bad', 'mensaje':u"Error al guardar los datos"})

            elif action == 'deletetematica':
                try:
                    tematica = Tematica.objects.get(pk=request.POST['id'])
                    if ComplexivoTematica.objects.filter(tematica=tematica).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u"La tematica ya ha fue aprobada por un director de carrera."})
                    tematica.status = False
                    tematica.save(request)
                    log(u"Elimino Tematica : %s" % tematica, request, "delete")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u"Error al eliminar los datos"})

            #ROL
            elif action == 'addrol':
                try:
                    form = ParticipanteRolForm(request.POST)
                    if form.is_valid():
                        if ParticipanteRol.objects.filter(rol=form.cleaned_data['rol'], status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El rol ya existe."})
                        rol = ParticipanteRol(rol=form.cleaned_data['rol'])
                        rol.save(request)
                        log(u'Agrego Rol en Investigación: %s' % rol, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editrol':
                try:
                    form = ParticipanteRolForm(request.POST)
                    if form.is_valid():
                        if ParticipanteRol.objects.filter(rol=form.cleaned_data['rol'], status=True).exclude(id=int(request.POST['id'])).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El rol ya existe."})
                        rol = ParticipanteRol.objects.get(id=int(request.POST['id']))
                        rol.rol = form.cleaned_data['rol']
                        rol.save(request)
                        log(u'Edito Rol en Investigación: %s' % rol, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delrol':
                try:
                    rol = ParticipanteRol.objects.get(id=int(request.POST['id']))
                    if ParticipanteGrupoInvestigacion.objects.filter(rol=rol).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, se esta utilizando en Participante."})
                    rol.delete()
                    log(u'Elimino Rol en Investigación: %s' % rol, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

                    # ROL

            #CONVOCATORIA
            # elif action == 'addrol':
            #         try:
            #             form = ParticipanteRolForm(request.POST)
            #             if form.is_valid():
            #                 if ParticipanteRol.objects.filter(rol=form.cleaned_data['rol'], status=True).exists():
            #                     return JsonResponse({"result": "bad", "mensaje": u"El rol ya existe."})
            #                 rol = ParticipanteRol(rol=form.cleaned_data['rol'])
            #                 rol.save(request)
            #                 log(u'Agrego Rol en Investigación: %s' % rol, request, "add")
            #                 return JsonResponse({"result": "ok"})
            #             else:
            #                 raise NameError('Error')
            #         except Exception as ex:
            #             transaction.set_rollback(True)
            #             return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editrol':
                    try:
                        form = ParticipanteRolForm(request.POST)
                        if form.is_valid():
                            if ParticipanteRol.objects.filter(rol=form.cleaned_data['rol'], status=True).exclude(
                                    id=int(request.POST['id'])).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"El rol ya existe."})
                            rol = ParticipanteRol.objects.get(id=int(request.POST['id']))
                            rol.rol = form.cleaned_data['rol']
                            rol.save(request)
                            log(u'Edito Rol en Investigación: %s' % rol, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delrol':
                try:
                    rol = ParticipanteRol.objects.get(id=int(request.POST['id']))
                    if ParticipanteGrupoInvestigacion.objects.filter(rol=rol).exists():
                        return JsonResponse({"result": "bad","mensaje": u"No puede eliminar, se esta utilizando en Participante."})
                    log(u'Elimino Rol en Investigación: %s' % rol, request, "add")
                    rol.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'vigente':
                try:
                    grupo = GrupoInvestigacion.objects.get(id=int(request.POST['id']))
                    if grupo.vigente:
                        grupo.vigente = False
                        grupo.tematica_set.filter(status=True).update(vigente=False)
                        log(u'Inavilito la vigencia del grupo de investigacion: %s la persona: %s' % (grupo, persona), request,"act")
                    else:
                        grupo.vigente = True
                        log(u'Habilito la vigencia del grupo de investigacion: %s la persona: %s' % (grupo, persona), request,"act")
                    grupo.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'vigente_tematica':
                try:
                    tematica = Tematica.objects.get(id=int(request.POST['id']))
                    if tematica.vigente:
                        tematica.vigente = False
                        log(u'Inavilito la vigencia de la línea de investigación: %s la persona: %s' % (tematica, persona), request,"act")
                    else:
                        tematica.vigente = True
                        log(u'habilito vigencia de la línea de investigación: %s la persona: %s' % (tematica, persona), request, "act")
                    tematica.save(request)

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addgrupo':
                try:
                    data['title'] = u"Añadir Grupo de Investigación"
                    form = GrupoInvestigacionForm()
                    # form.profesor_nombramiento()
                    data['form'] = form
                    return render(request, "adm_grupoinvestigacion/addgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editgrupo':
                try:
                    data['title'] = u"Editar Grupo de Investigación"
                    data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    if grupo.director_id in [None, '', 0]:
                        data['idcodigodirector'] = iddirector = 0
                    else:
                        data['idcodigodirector'] = iddirector = grupo.director.id
                    if grupo.codirector_id in [None, '', 0]:
                        data['idcodigocodirector'] = idcodirector = 0
                    else:
                        data['idcodigocodirector'] = idcodirector = grupo.codirector.id
                    form = GrupoInvestigacionForm(initial={
                        'nombre': grupo.nombre,
                        'director': iddirector,
                        'codirector': idcodirector,
                        'descripcion': grupo.descripcion,
                        'fechapresentacion': grupo.fechapresentacion,
                        'fecharesolucion': grupo.fecharesolucion,
                        'resolucion':grupo.resolucion,
                        'observacion': grupo.observacion,
                    })
                    # form.profesor_nombramiento()
                    lista = []
                    for lin in grupo.lineasgrupoinvestigacion_set.all():
                        if LineasTematica.objects.filter(linea=lin, tematica__grupo= grupo ).exists():
                            lista.append(lin.linea.id)
                    data['lista_no_editar'] = lista
                    data['lista_lineas'] = grupo.lineasgrupoinvestigacion_set.all()
                    data['form'] = form
                    return render(request, "adm_grupoinvestigacion/editgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletegrupo':
                try:
                    data['title'] = u'Eliminar Grupo de Investigación'
                    data['grupo'] = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_grupoinvestigacion/deletegrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'participantes':
                try:
                    data['title'] =u"Participante Grupo de Investigación"
                    data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    if 's' in request.GET:
                        data['consultado'] = request.GET['s']
                    if 'vigente' in request.GET:
                        data['vigente'] = request.GET['vigente']
                    data['participantes'] = grupo.participantegrupoinvestigacion_set.filter(status=True).order_by('persona__apellido1','persona__apellido2','persona__nombres')
                    return render(request, "adm_grupoinvestigacion/viewparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparticipante':
                try:
                    data['title'] = u"Añadir Participante de Investigación"
                    data['grupo'] = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    form= ParticipanteGrupoInvestigacionForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "adm_grupoinvestigacion/addparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editparticipante':
                try:
                    data['title'] = u"Editar Participante de Investigación"
                    data['participante'] = participante= ParticipanteGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['grupo'] = participante.grupo
                    if participante.tipo==2:
                        form= ParticipanteGrupoInvestigacionForm(initial={
                            'cedula': participante.cedula,
                            'nombre' : participante.nombre,
                            'apellido': participante.apellido,
                            'correo' : participante.correo,
                            'institucion' : participante.institucion,
                            'formacion': participante.formacion,
                            'rol': participante.rol,
                            'participante':participante.tipo
                        })
                        form.deshabilitar_busqueda()
                    else:
                        form= ParticipanteGrupoInvestigacionForm(initial={
                            'cedula': participante.persona.cedula,
                            'nombre' : participante.persona.nombres,
                            'apellido': participante.persona.apellido1+" "+participante.persona.apellido2,
                            'correo' : participante.persona.email,
                            'institucion' : 'UNEMI',
                            'formacion': participante.persona.titulacion_principal_senescyt(),
                            'rol': participante.rol,
                            'participante':participante.tipo
                        })
                        form.adicionar()
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    data['form'] = form
                    return render(request, "adm_grupoinvestigacion/editparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteparticipante':
                try:
                    data['title'] = u'Eliminar Participante'
                    data['participante'] = participante =ParticipanteGrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['grupo']= participante.grupo
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    return render(request, "adm_grupoinvestigacion/deleteparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'busqueda':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__()==2:
                        personas = Persona.objects.filter(Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1]) & Q(tipopersona=1))[:20]
                    else:
                        personas = Persona.objects.filter((Q(cedula__contains=s[0]) | Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q( apellido2__contains=s[0]) | Q(nombres__contains=s[0]))& Q(tipopersona=1))[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(), "cedula": x.cedula, "nombre":x.nombres, "apellido": x.apellido1 +" "+ x.apellido2, "correo":x.email, "formacion":x.titulacion_principal_senescyt()} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad'})

            elif action == 'busquedaparticipante':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s)== 1:
                        personas = Persona.objects.filter(Q(cedula__contains=q) | Q(nombres__contains=q) | Q(apellido1__contains=q) | Q(apellido2__contains=q))[:20]
                    else:
                        personas = Persona.objects.filter(Q(nombres__contains=s[0]) |Q(apellido1__contains=s[0]) | Q(apellido2__contains=s[1]))[:20]

                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(), "cedula": x.cedula, "nombre":x.nombres, "apellido": x.apellido1 +" "+ x.apellido2, "correo":x.email} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad'})

            elif action == 'tematicas':
                try:
                    data['title'] = u"Grupo de Investigación"
                    data['tematicas'] = Tematica.objects.filter(grupo_id=request.GET['id'], status=True)
                    if 's' in request.GET:
                        data['consultado'] = request.GET['s']
                    if 'vigente' in request.GET:
                        data['vigente'] = request.GET['vigente']
                    data['grupo'] = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_grupoinvestigacion/viewtematicas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtematica':
                try:
                    data['title'] = u"Añadir línea de investigación"
                    data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=request.GET['id'])
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    form = TematicaGrupoInvestigacionForm()
                    form.cargar_lineas(grupo)
                    data['form'] = form
                    return render(request, "adm_grupoinvestigacion/addtematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittematica':
                try:
                    data['title'] = u"Editar línea de investigación"
                    data['tematica']= tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    data['grupo'] = tematica.grupo
                    form = TematicaGrupoInvestigacionForm(initial={'tema': tematica.tema, 'tipopublicacion': tematica.tipopublicacion})
                    form.cargar_lineas(tematica.grupo)
                    data['form'] = form
                    data['lista_lineas'] = tematica.lineastematica_set.all()
                    return render(request, "adm_grupoinvestigacion/edittematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletetematica':
                try:
                    data['title'] = u"Eliminar línea de investigación"
                    data['tematica'] = tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    data['grupo'] = tematica.grupo
                    return render(request, "adm_grupoinvestigacion/deletetematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'detailtematica':
                try:
                    data['title'] = u"Detalle línea de investigación"
                    data['tematica'] = tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    data['grupo'] = tematica.grupo
                    data['participantes'] = tematica.participantetematica_set.filter(status=True)
                    return render(request, "adm_grupoinvestigacion/detailtematica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparticipantetematica':
                try:
                    data['title'] = u"Participantes de línea de investigación"
                    data['tematica'] = tematica = Tematica.objects.get(pk=request.GET['id'])
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    lista = tematica.participantetematica_set.values_list('participante').filter(status=True)
                    if lista.count() > 0:
                        data['participantes'] = tematica.grupo.participantegrupoinvestigacion_set.filter(status=True).exclude(pk__in =lista)
                    else:
                        data['participantes'] = tematica.grupo.participantegrupoinvestigacion_set.filter(status=True)
                    return render(request, "pro_grupo_investigacion/listaparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalle':
                try:
                    data['grupo'] = grupo = GrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    template = get_template("adm_grupoinvestigacion/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'deleteparticipantetematica':
                try:
                    data['title'] = u"Eliminar participante"
                    data['participante'] = participante = ParticipanteTematica.objects.get(pk=request.GET['id'])
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    data['tematica'] = participante.tematica
                    return render(request, "pro_grupo_investigacion/deleteparticipantetematica.html", data)
                except Exception as ex:
                    pass

            #ROL
            elif action == 'addrol':
                try:
                    data['title'] =u"Adicionar rol"
                    data['form'] = ParticipanteRolForm()
                    return render(request, "adm_grupoinvestigacion/addrol.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrol':
                try:
                    data['title'] =u"Editar rol"
                    data['rol']= rol=ParticipanteRol.objects.get(id=int(request.GET['id']))
                    data['form'] = ParticipanteRolForm(initial={'rol':rol.rol})
                    return render(request, "adm_grupoinvestigacion/editrol.html", data)
                except Exception as ex:
                    pass

            elif action == 'delrol':
                try:
                    data['title'] = u'Eliminar rol'
                    data['rol'] = ParticipanteRol.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_grupoinvestigacion/delrol.html", data)
                except Exception as ex:
                    pass

            elif action == 'rol':
                try:
                    data['title'] =u"Rol"
                    data['roles'] = ParticipanteRol.objects.filter(status=True)
                    return render(request, "adm_grupoinvestigacion/viewrol.html", data)
                except Exception as ex:
                    pass

            # CONVOCATORIA
            elif action == 'addconvocaria':
                    try:
                        data['title'] = u"Adicionar rol"
                        data['form'] = ParticipanteRolForm()
                        return render(request, "adm_grupoinvestigacion/addrol.html", data)
                    except Exception as ex:
                        pass

            elif action == 'editconvocaria':
                try:
                    data['title'] = u"Editar rol"
                    data['rol'] = rol = ParticipanteRol.objects.get(id=int(request.GET['id']))
                    data['form'] = ParticipanteRolForm(initial={'rol': rol.rol})
                    return render(request, "adm_grupoinvestigacion/editrol.html", data)
                except Exception as ex:
                    pass

            elif action == 'delconvocaria':
                try:
                    data['title'] = u'Eliminar rol'
                    data['rol'] = ParticipanteRol.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_grupoinvestigacion/delrol.html", data)
                except Exception as ex:
                    pass

            elif action == 'convocaria':
                try:
                    data['title'] = u"Rol"
                    data['roles'] = ParticipanteRol.objects.filter(status=True)
                    return render(request, "adm_grupoinvestigacion/viewrol.html", data)
                except Exception as ex:
                    pass

            elif action == 'vigente':
                try:
                    data['grupo'] = grupo =  GrupoInvestigacion.objects.get(status=True, pk=int(request.GET['id']))
                    if grupo.vigente:
                        data['title'] = u"Desactivar grupo de Investigación"
                    else:
                        data['title'] = u"Activar grupo de Investigación"
                    return render(request, "adm_grupoinvestigacion/vigente.html", data)
                except Exception as ex:
                    pass

            elif action == 'vigente_tematica':
                try:
                    data['tematica'] = tematica =  Tematica.objects.get(status=True, pk=int(request.GET['id']))
                    data['consultado'] = request.GET['s']
                    data['vigente'] = request.GET['vigente']
                    if tematica.vigente:
                        data['title'] = u"Desactivar Línea de investigación"
                    else:
                        data['title'] = u"Activar Línea de investigación"
                    return render(request, "adm_grupoinvestigacion/vigente_tematica.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u"Investigación"
            # grupos = GrupoInvestigacion.objects.filter(status=True).order_by('id')
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if 'vigente' in request.GET:
                    if request.GET['vigente'] != '':
                        if int(request.GET['vigente'])>0:
                            if len(ss) == 1:
                                grupos = GrupoInvestigacion.objects.filter(status=True, nombre__icontains=search, vigente=True if int(request.GET['vigente']) == 1 else False).order_by('id')
                            elif len(ss) == 2:
                                grupos = GrupoInvestigacion.objects.filter(Q(status=True), Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1]), vigente=True if int(request.GET['vigente']) == 1 else False).order_by('id')
                            else:
                                grupos = GrupoInvestigacion.objects.filter(Q(status=True), Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1]), Q(nombre__icontains=ss[2]), vigente=True if int(request.GET['vigente']) == 1 else False).order_by('id')
                        else:
                            if len(ss) == 1:
                                grupos = GrupoInvestigacion.objects.filter(status=True, nombre__icontains=search).order_by('id')
                            elif len(ss) == 2:
                                grupos = GrupoInvestigacion.objects.filter(Q(status=True), Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1])).order_by('id')
                            else:
                                grupos = GrupoInvestigacion.objects.filter(Q(status=True), Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1]), Q(nombre__icontains=ss[2])).order_by('id')
                    else:
                        if len(ss) == 1:
                            grupos = GrupoInvestigacion.objects.filter(status=True,
                                                                       nombre__icontains=search).order_by('id')
                        elif len(ss) == 2:
                            grupos = GrupoInvestigacion.objects.filter(Q(status=True), Q(nombre__icontains=ss[0]),
                                                                       Q(nombre__icontains=ss[1])).order_by('id')
                        else:
                            grupos = GrupoInvestigacion.objects.filter(Q(status=True), Q(nombre__icontains=ss[0]),
                                                                       Q(nombre__icontains=ss[1]),
                                                                       Q(nombre__icontains=ss[2])).order_by('id')
                else:
                    if len(ss) == 1:
                        grupos = GrupoInvestigacion.objects.filter(status=True, nombre__icontains=search).order_by('id')
                    elif len(ss) == 2:
                        grupos = GrupoInvestigacion.objects.filter(Q(status=True), Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1])).order_by('id')
                    else:
                        grupos = GrupoInvestigacion.objects.filter(Q(status=True), Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1]), Q(nombre__icontains=ss[2])).order_by('id')
            elif 'vigente' in request.GET:
                if request.GET['vigente'] != '':
                    if int(request.GET['vigente']) > 0:
                        grupos = GrupoInvestigacion.objects.filter(status=True, vigente=True if int(request.GET['vigente']) == 1 else False).order_by('id')
            else:
                grupos = GrupoInvestigacion.objects.filter(status=True).order_by('id')

            if 'vigente' in request.GET:
                if request.GET['vigente'] != '':
                    data['vigente'] = int(request.GET['vigente'])

            paging = MiPaginador(grupos, 10)
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
            return render(request, "adm_grupoinvestigacion/viewgrupo.html", data)

