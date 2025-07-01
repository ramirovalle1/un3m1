# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import PropuestaTitulacionForm,  DocumentoPersonalesFrom
from sga.funciones import log, generar_nombre
from sga.models import Inscripcion, miinstitucion, MatriculaTitulacion, AlternativaTitulacion, PropuestaTitulacion, \
    PropuestaLineaInvestigacion_Carrera, PropuestaSubLineaInvestigacion, PropuestaTitulacion_Matricula, CUENTAS_CORREOS, \
    ArchivoTitulacion
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}

    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcion']=inscripcion = perfilprincipal.inscripcion
    lista=""

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                form = PropuestaTitulacionForm(request.POST)
                if form.is_valid():
                    if PropuestaTitulacion.objects.filter(Q(tema=form.cleaned_data['tema']) & Q(estado=1)| Q( estado=2)).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un proyecto con este titulo registrado."})
                    listado = request.POST['otrosintegrantes']
                    integrantes = Inscripcion.objects.filter(id__in=[int(x) for x in listado.split(',')]) if listado else []
                    if integrantes.values('id').count()<3:
                        propuesta= PropuestaTitulacion(
                                                       tema=form.cleaned_data['tema'],
                                                       lineainvestigacion=form.cleaned_data['lineainvestigacion'],
                                                       sublineainvestigacion=form.cleaned_data['sublineainvestigacion'],
                                                       palabrasclaves=form.cleaned_data['palabrasclaves'],
                                                       fechaentrega=datetime.now().date(),
                                                       problema=form.cleaned_data['problema'],
                                                       objetivogeneral=form.cleaned_data['objetivogeneral'],
                                                       objetivoespecifico=form.cleaned_data['objetivoespecifico'],
                                                       metodo=form.cleaned_data['metodo'],
                                                       descripcionpropuesta=form.cleaned_data['descripcionpropuesta'],
                                                       resultadoesperado=form.cleaned_data['resultadoesperado'],
                                                       referencias=form.cleaned_data['referencias']
                                                       )
                        propuesta.save(request)
                        log(u'Añadir Propuesta Titulación: %s' % propuesta, request, "add")
                        for integrante in integrantes:
                            mat = MatriculaTitulacion.objects.get(inscripcion_id=integrante.id, estado=6)
                            pro_mat = PropuestaTitulacion_Matricula(propuesta_id=propuesta.id,matricula_id=mat.id)
                            pro_mat.save(request)
                            log(u'Añadir Propuesta Titulación a estudiantes: %s' % propuesta, request, "add")
                            if not inscripcion == integrante:
                                mat.estado=7
                            else:
                                mat.estado=1
                            mat.save(request)
                            send_html_mail("Registro anteproyecto", "emails/nuevoanteproyecto.html",{'sistema': request.session['nombresistema'], 'Propuesta': propuesta,
                                        't': miinstitucion()}, inscripcion.persona.lista_emails_envio(),[], cuenta=CUENTAS_CORREOS[16][1])
                        log(u'Editar Matricula Titulación: %s' % mat, request, "editar")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad","mensaje": u"La cantidad de integrantes para el proyecto sobrepasa el limite."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editpropuestatitulacion':
            try:
                form = PropuestaTitulacionForm(request.POST)
                if form.is_valid():
                    integrantes=''
                    num_integrantes=0
                    propuesta = PropuestaTitulacion.objects.get(pk=request.POST['id'])
                    if PropuestaTitulacion.objects.filter(Q(tema=form.cleaned_data['tema']) & (Q(estado=1)| Q( estado=2))).exclude(id=propuesta.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un proyecto con este titulo registrado."})
                    if propuesta.numero_integrantes()==1:
                        listado = request.POST['otrosintegrantes']
                        integrantes = Inscripcion.objects.filter(id__in=[int(x) for x in listado.split(',')]) if listado else []
                        num_integrantes = integrantes.values('id').count()
                    else:
                        num_integrantes=2
                    if num_integrantes<3:
                        propuesta.tema = form.cleaned_data['tema']
                        propuesta.lineainvestigacion = form.cleaned_data['lineainvestigacion']
                        propuesta.sublineainvestigacion = form.cleaned_data['sublineainvestigacion']
                        propuesta.palabrasclaves = form.cleaned_data['palabrasclaves']
                        propuesta.fechaentrega = datetime.now().date()
                        propuesta.problema = form.cleaned_data['problema']
                        propuesta.objetivogeneral = form.cleaned_data['objetivogeneral']
                        propuesta.objetivoespecifico = form.cleaned_data['objetivoespecifico']
                        propuesta.metodo = form.cleaned_data['metodo'],
                        propuesta.descripcionpropuesta = form.cleaned_data['descripcionpropuesta']
                        propuesta.resultadoesperado = form.cleaned_data['resultadoesperado']
                        propuesta.referencias = form.cleaned_data['referencias']
                        propuesta.save(request)
                        log(u'Editar Propuesta Titulación: %s' % propuesta, request, "editar")
                        if propuesta.numero_integrantes() == 1:
                            for integrante in integrantes:
                                mat = MatriculaTitulacion.objects.get(inscripcion_id=integrante.id, estado=1)
                                if not mat.inscripcion==inscripcion:
                                    pro_mat = PropuestaTitulacion_Matricula(propuesta_id=propuesta.id,matricula_id=mat.id)
                                    pro_mat.save(request)
                                    log(u'Rechazo Propuesta Titulación: %s' % pro_mat, request, "add")
                                if not inscripcion == integrante:
                                    mat.estado=7
                                mat.save(request)
                                log(u'Matricula de Titulación: %s' % mat, request, "editar")
                                send_html_mail("Registro anteproyecto", "emails/nuevoanteproyecto.html",{'sistema': request.session['nombresistema'], 'Propuesta': propuesta,
                                            't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[16][1])
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad","mensaje": u"La cantidad de integrantes para el proyecto sobrepasa el limite."})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'elipropuestatitulacion':
            try:
                matricula= MatriculaTitulacion.objects.get(Q(inscripcion=inscripcion), (Q(estado=6) | Q(estado=1)))
                pro_mat = PropuestaTitulacion_Matricula.objects.get(propuesta_id=int(request.POST['id']),matricula=matricula, status=True)
                if pro_mat.propuesta.numero_integrantes()==1:
                    pro_mat.status=False
                    pro_mat.save(request)
                    log(u'Elimino Propuesta de Titulacion: %s' % pro_mat, request, "del")
                    matricula = MatriculaTitulacion.objects.get(pk=pro_mat.matricula_id)
                    matricula.estado=6
                    log(u'Elimino Propuesta de Titulacion: %s' % matricula, request, "del")
                    propuesta=PropuestaTitulacion.objects.get(pk=int(request.POST['id']))
                    propuesta.status=4
                    propuesta.save(request)
                    log(u'Elimino Integrante Propuesta de Titulacion: %s' % propuesta, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    propuesta = PropuestaTitulacion.objects.get(pk=int(request.POST['id']), status=True)
                    pro_mat= PropuestaTitulacion_Matricula.objects.filter(propuesta=propuesta, status=True)
                    for pro in pro_mat:
                        if pro.matricula.estado==7 and not pro.matricula.inscripcion==inscripcion:
                            pro.status=False
                            pro.save(request)
                            log(u'Elimino Integrante Propuesta de Titulacion: %s' % pro, request, "del")
                            matricula= MatriculaTitulacion.objects.get(pk=pro.matricula_id)
                            matricula.estado=6
                            matricula.save(request)
                            log(u'Elimino Propuesta  de Titulacion: %s' % matricula, request, "del")
                        else:
                            if pro.matricula.inscripcion==inscripcion:
                                pro.status = False
                                pro.save(request)
                                log(u'Elimino la Propuesta de Titulacion: %s' % pro, request, "del")
                                matricula = MatriculaTitulacion.objects.get(pk=pro.matricula_id)
                                matricula.estado = 6
                                matricula.save(request)
                                log(u'Elimino Propuesta  de Titulacion: %s' % matricula, request, "del")
                    return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'cancelarmatricula':
            try:
                matricula = MatriculaTitulacion.objects.get(Q(inscripcion=inscripcion), (Q(estado=6) | Q(estado=1)))
                if PropuestaTitulacion_Matricula.objects.filter(matricula=matricula, status=True).exists():
                    pro_mat = PropuestaTitulacion_Matricula.objects.get(matricula=matricula, status=True)
                    if pro_mat.propuesta.numero_integrantes()==1:
                        pro_mat.status=False
                        pro_mat.save(request)
                        log(u'Elimino Propuesta de Titulacion: %s' % pro_mat, request, "del")
                        matricula = MatriculaTitulacion.objects.get(pk=pro_mat.matricula_id)
                        matricula.estado=4
                        log(u'Elimino Propuesta de Titulacion: %s' % matricula, request, "del")
                        propuesta=PropuestaTitulacion.objects.get(pk=pro_mat.propuesta_id)
                        propuesta.estado=5
                        propuesta.save(request)
                        log(u'Elimino Integrante Propuesta de Titulacion: %s' % propuesta, request, "del")
                        return JsonResponse({"result": "ok"})
                    else:
                        propuesta = PropuestaTitulacion.objects.get(pk=pro_mat.propuesta_id, estado=1)
                        pro_mat= PropuestaTitulacion_Matricula.objects.filter(propuesta=propuesta, status=True)
                        for pro in pro_mat:
                            if pro.matricula.estado==7 and not pro.matricula.inscripcion==inscripcion:
                                pro.status=False
                                pro.save(request)
                                log(u'Elimino Integrante Propuesta de Titulacion: %s' % pro, request, "del")
                                matricula= MatriculaTitulacion.objects.get(pk=pro.matricula_id)
                                matricula.estado=6
                                matricula.save(request)
                                log(u'Elimino Propuesta  de Titulacion: %s' % matricula, request, "del")
                            else:
                                if pro.matricula.inscripcion==inscripcion:
                                    pro.status = False
                                    pro.save(request)
                                    log(u'Elimino la Propuesta de Titulacion: %s' % pro, request, "del")
                                    matricula = MatriculaTitulacion.objects.get(pk=pro.matricula_id)
                                    matricula.estado = 4
                                    matricula.save(request)
                                    log(u'Elimino Propuesta  de Titulacion: %s' % matricula, request, "del")
                        return JsonResponse({"result": "ok"})
                else:
                    matricula.estado=4
                    matricula.save(request)
                    log(u'Elimino Propuesta  de Titulacion: %s' % matricula, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'retirarseproceso':
            try:
                matricula = MatriculaTitulacion.objects.get(inscripcion=inscripcion,estado=1)
                pro_mat = PropuestaTitulacion_Matricula.objects.get(matricula=matricula, status=True)
                if pro_mat.propuesta.numero_integrantes()==1:
                    pro_mat.status=False
                    pro_mat.save(request)
                    log(u'Retirado Proceso de Titulación: %s' % pro_mat, request, "del")
                    matricula = MatriculaTitulacion.objects.get(pk=pro_mat.matricula_id)
                    matricula.estado=2
                    log(u'Retirado Proceso de Titulacion: %s' % matricula, request, "del")
                    propuesta=PropuestaTitulacion.objects.get(pk=pro_mat.propuesta_id)
                    propuesta.estado=5
                    propuesta.save(request)
                    log(u'Elimino Integrante Propuesta de Titulacion: %s' % propuesta, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    propuesta = PropuestaTitulacion.objects.get(pk=pro_mat.propuesta_id, estado=1)
                    pro_mat= PropuestaTitulacion_Matricula.objects.filter(propuesta=propuesta, status=True)
                    for pro in pro_mat:
                        if pro.matricula.estado==7 and not pro.matricula.inscripcion==inscripcion:
                            pro.status=False
                            pro.save(request)
                            log(u'Elimino Integrante Propuesta de Titulacion: %s' % pro, request, "del")
                            matricula= MatriculaTitulacion.objects.get(pk=pro.matricula_id)
                            matricula.estado=2
                            matricula.save(request)
                            log(u'Elimino Propuesta  de Titulacion: %s' % matricula, request, "del")
                        else:
                            if pro.matricula.inscripcion==inscripcion:
                                pro.status = False
                                pro.save(request)
                                log(u'retirado de Propuesta de Titulacion: %s' % pro, request, "del")
                                matricula = MatriculaTitulacion.objects.get(pk=pro.matricula_id)
                                matricula.estado = 2
                                matricula.save(request)
                                log(u'Retirado de Proceso de Titulación: %s' % matricula, request, "del")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        if action == 'confirmar':
            try:
                matricula= MatriculaTitulacion.objects.get(estado=7,inscripcion_id=inscripcion.id)
                matricula.estado=1
                matricula.save(request)
                log(u'Confirma Propuesta Titulación: %s' % matricula, request, "editar")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        if action == 'rechazar':
            try:
                matricula= MatriculaTitulacion.objects.get(estado=7,inscripcion_id=inscripcion.id)
                matricula.estado=6
                matricula.save(request)
                log(u'Rechazo Propuesta Titulación: %s' % matricula, request, "editar")
                propuesta=PropuestaTitulacion_Matricula.objects.get(matricula=matricula, status=True)
                propuesta.status=False
                propuesta.save(request)
                log(u'Rechazo Propuesta Titulación: %s' % propuesta, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargardocumento':
            try:
                newfilecedula = None
                newfilevotacion = None
                arch = DocumentoPersonalesFrom(request.POST, request.FILES)
                if arch.is_valid():
                    if 'cedula' in request.FILES and 'votacion' in request.FILES:
                        newfilecedula = request.FILES['cedula']
                        newfilecedula._name = generar_nombre("DocumentoPersonal_", newfilecedula._name)
                        newfilevotacion = request.FILES['votacion']
                        newfilevotacion._name = generar_nombre("DocumentoPersonal_", newfilevotacion._name)
                    matricula = MatriculaTitulacion.objects.get(pk=int(request.POST['id']))
                    matricula.documento_cedula = newfilecedula
                    matricula.documento_certificado_votacion=newfilevotacion
                    matricula.save(request)
                    log(u'Matriculaa añadir documento :%s' % matricula, request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u"Los documentos se han gargado correctamente"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Solo se permite documentos pdf"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'busqueda':
                try:
                    alter = AlternativaTitulacion.objects.get(pk=int(request.GET['alternativa_id']))
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        ins= MatriculaTitulacion.objects.filter(inscripcion__persona__apellido1__icontains=s[0],inscripcion__persona__apellido2__icontains=s[1],alternativa__carrera=inscripcion.carrera, alternativa_id=alter.id).exclude(Q(estado=1)|Q(estado=3)|Q(estado=7)|Q(estado=2)|Q(inscripcion_id=inscripcion.id)).distinct()
                    else:
                        ins = MatriculaTitulacion.objects.filter((Q(inscripcion__persona__nombres__contains=s[0])| Q(inscripcion__persona__apellido1__contains=s[0]) | Q(inscripcion__persona__apellido2__contains=s[0]) | Q(inscripcion__persona__cedula__contains=s[0]))).filter(alternativa__carrera=inscripcion.carrera,alternativa_id=alter.id).exclude((Q(estado=1)|Q(estado=3)|Q(estado=7)|Q(estado=2))|Q(inscripcion_id=inscripcion.id)).distinct()
                    data = {"result": "ok", "results": [{"id": x.inscripcion_id, "name": x.flexbox_repr()}for x in ins]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'infopropuestatitulacion':
                try:
                    data['title'] = u'Información del proyecto'
                    data['permite_modificar'] = False
                    data['inscripcion'] = inscripcion
                    data['alternativatitulacion'] = alter = AlternativaTitulacion.objects.get(pk=int(request.GET['id']))
                    matricula = MatriculaTitulacion.objects.get(inscripcion=inscripcion, estado= 1)
                    pro_mat = PropuestaTitulacion_Matricula.objects.get(matricula=matricula)
                    form = PropuestaTitulacionForm(initial={'tema':pro_mat.propuesta.tema,
                                                            'lineainvestigacion':pro_mat.propuesta.lineainvestigacion,
                                                            'sublineainvestigacion':pro_mat.propuesta.sublineainvestigacion,
                                                            'palabrasclaves':pro_mat.propuesta.palabrasclaves,
                                                            'tipotrabajotitulacion': alter.tipotitulacion,
                                                            'problema':pro_mat.propuesta.problema,
                                                            'objetivogeneral':pro_mat.propuesta.objetivogeneral,
                                                            'objetivoespecifico':pro_mat.propuesta.objetivoespecifico,
                                                            'metodo':pro_mat.propuesta.metodo,
                                                            'descripcionpropuesta':pro_mat.propuesta.descripcionpropuesta,
                                                            'resultadoesperado':pro_mat.propuesta.resultadoesperado,
                                                            'referencias':pro_mat.propuesta.referencias
                                                            })
                    form.editar()
                    data['form'] = form
                    return render(request, "alu_propuestatitulacion/editpropuestatitulacion.html", data)
                except Exception as ex:
                    pass

            if action=='elipropuestatitulacion':
                try:
                    data['title'] = u'Eliminar Tipo Titulación'
                    data['propuesta'] = PropuestaTitulacion.objects.get(pk=int(request.GET['id']), estado=1)
                    return render(request, "alu_propuestatitulacion/elipropuestatitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addpropuestatitulacion':
                try:
                    data['title'] = u'Añadir Propuesta de Titulación'
                    data['inscripcion'] = inscripcion
                    data['alternativatitulacion'] = alter = AlternativaTitulacion.objects.get(pk=int(request.GET['id']))
                    form = PropuestaTitulacionForm(initial={'tipotrabajotitulacion': alter.tipotitulacion})
                    form.no_modificar()
                    data['form'] = form
                    return render(request, "alu_propuestatitulacion/addpropuestatitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editpropuestatitulacion':
                try:
                    data['title'] = u'Editar Propuesta de Titulación'
                    data['inscripcion'] = inscripcion
                    data['alternativatitulacion'] = alter = AlternativaTitulacion.objects.get(pk=int(request.GET['id']))
                    matricula = MatriculaTitulacion.objects.get(inscripcion=inscripcion,estado=1)
                    pro_mat = PropuestaTitulacion_Matricula.objects.get(matricula=matricula,status=True)
                    form = PropuestaTitulacionForm(initial={'tema':pro_mat.propuesta.tema,
                                                            'lineainvestigacion':pro_mat.propuesta.lineainvestigacion,
                                                            'sublineainvestigacion':pro_mat.propuesta.sublineainvestigacion,
                                                            'palabrasclaves':pro_mat.propuesta.palabrasclaves,
                                                            'tipotrabajotitulacion': alter.tipotitulacion,
                                                            'problema':pro_mat.propuesta.problema,
                                                            'objetivogeneral':pro_mat.propuesta.objetivogeneral,
                                                            'objetivoespecifico':pro_mat.propuesta.objetivoespecifico,
                                                            'metodo':pro_mat.propuesta.metodo,
                                                            'descripcionpropuesta':pro_mat.propuesta.descripcionpropuesta,
                                                            'resultadoesperado':pro_mat.propuesta.resultadoesperado,
                                                            'referencias':pro_mat.propuesta.referencias
                                                            })
                    form.no_modificar()
                    data['form'] = form
                    data['propuesta_id']=pro_mat.propuesta_id
                    if pro_mat.propuesta.numero_integrantes()==1:
                        data['agrega_integrantes']=True
                    return render(request, "alu_propuestatitulacion/editpropuestatitulacion.html", data)
                except Exception as ex:
                    pass
            if action=='cancelarmatricula':
                try:
                    data['title'] = u'Eliminar Incripción'
                    matricula= MatriculaTitulacion.objects.get(Q(inscripcion= inscripcion),(Q(estado=6) | Q(estado=1)))
                    if PropuestaTitulacion_Matricula.objects.filter(matricula=matricula,status=True).exists():
                        pro_mat=PropuestaTitulacion_Matricula.objects.get(matricula=matricula,status=True)
                        data['propuesta'] = pro_mat.propuesta
                    else:
                        data['propuesta'] = u'Seguro desea cancelar la matricula'
                    return render(request, "alu_propuestatitulacion/cancelarmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'retirarseproceso':
                try:
                    data['title'] = u'Retirarse del Porceso de Titulación'
                    matricula = MatriculaTitulacion.objects.get(inscripcion=inscripcion, estado=1, status=True)
                    if PropuestaTitulacion_Matricula.objects.filter(matricula=matricula, status=True).exists():
                        pro_mat=PropuestaTitulacion_Matricula.objects.get(matricula=matricula,status=True)
                        data['propuesta'] = pro_mat.propuesta
                    else:
                        data['propuesta'] = u'Seguro desea cancelar la matricula'
                    return render(request, "alu_propuestatitulacion/retirarseproceso.html", data)
                except Exception as ex:
                    pass

            if action == 'cargarlineas':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')
                    listalg = []
                    lineas= PropuestaLineaInvestigacion_Carrera.objects.filter(carrera_id=inscripcion.carrera_id)
                    for lista in lineas:
                        listalg.append([lista.linea_id, lista.linea.nombre])
                    data = {"results": "ok", 'listalg':listalg}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'cargarsublineas':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')
                    if 'linea_id' in request.GET:
                        lista = []
                        lineas= PropuestaSubLineaInvestigacion.objects.filter(linea=int(request.GET['linea_id']))
                        for lis in lineas:
                            lista.append([lis.id, lis.nombre])
                        data = {"results": "ok", 'lista':lista}
                        return JsonResponse(data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            if not MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),(Q(estado=6)|Q(estado=1)|Q(estado=7)),(Q(alternativa__fechamatriculacion__gte=datetime.now())& Q(alternativa__fechamatriculacionfin__lte=datetime.now()))).exists():
                if MatriculaTitulacion.objects.filter(inscripcion=inscripcion).exists():
                    data['mat_cerrada']=True
            if not MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),(Q(estado=6)|Q(estado=1)|Q(estado=7))).exists():
                data['title'] = u'Matriculación al Proceso de Titulación'
                if inscripcion.graduado():
                    return HttpResponseRedirect("/?info=Ingreso no permitido a graduados.")
                if MatriculaTitulacion.objects.values('id').filter(Q(inscripcion=inscripcion),(Q(estado=2) | Q(estado=5))).count() >= 3:
                    return HttpResponseRedirect("/?info=Tiene más de 3 matriculas")
                else:
                    if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), Q(estado=1)).exists():
                        return render(request, "alu_propuestatitulacion/view.html", data)
                        # return HttpResponseRedirect("/?info=Usted ya cuenta con un proyecto vigente.")
                    if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), Q(estado=7)).exists():
                        return HttpResponseRedirect("/?info=Usted ya cuenta con un proyecto vigente de confirmar.")
                    alucarrera = inscripcion.carrera
                    data['inscripcion'] = inscripcion
                    data['alternativa'] = AlternativaTitulacion.objects.filter(Q(carrera=alucarrera) & (Q(fechamatriculacion__lte=datetime.now().date()) & Q(fechamatriculacionfin__gte=datetime.now().date()))).exclude(Q(status=False)| Q(verestudiantes=False))
                    # data['alternativa'] = AlternativaTitulacion.objects.filter(Q(carrera=alucarrera)& ((Q(fechamatriculacion__lte=datetime.now().date())& Q(fechamatriculacionfin__gte=datetime.now().date())) | (Q(fechaordinariainicio__lte=datetime.now().date())& Q(fechaordinariafin__gte=datetime.now().date()))| (Q(fechaextraordinariainicio__lte=datetime.now().date())& Q(fechaextraordinariafin__gte=datetime.now().date()))| (Q(fechaespecialinicio__lte=datetime.now().date())& Q(fechaespecialfin__gte=datetime.now().date())))).exclude(status=False)
                    return render(request, "alu_matriculaciontitulacion/view.html", data)
            data['matricula'] = matricula = MatriculaTitulacion.objects.get(Q(inscripcion=inscripcion)& (Q(estado=6)|Q(estado=1)| Q(estado=7)))
            data['propuestas'] = PropuestaTitulacion_Matricula.objects.filter(matricula=matricula, status=True)
            if MatriculaTitulacion.objects.filter(inscripcion_id=inscripcion.id, estado=7).exists():
                try:
                    data['title'] = u'Confirmación'
                    pro_mat= PropuestaTitulacion_Matricula.objects.get(matricula=matricula, matricula__estado=7, status=True)
                    data['tema']=pro_mat.propuesta.tema
                    # if pro_mat.matricula.inscripcion==inscripcion:
                    data['estudiante']=pro_mat.matricula.inscripcion
                    return render(request, "alu_propuestatitulacion/confirmacionestudiante.html", data)
                except Exception as ex:
                    pass
            archivo = MatriculaTitulacion.objects.get(Q(inscripcion=inscripcion), (Q(estado=1) | Q(estado=6)))
            if not (archivo.tiene_cedula() and archivo.tiene_certificado_votacion()):
                try:
                    data['title'] = u'Añadir Documentos Personales'
                    data['form'] = DocumentoPersonalesFrom()
                    return render(request, "alu_propuestatitulacion/cargardocumentospersonales.html", data)
                except Exception as ex:
                    pass

            data['title'] = u'Propuesta de Titulación'
            data['alternativa'] = alternativa = matricula.alternativa
            data['examen']= True if matricula.alternativa.tipotitulacion.tipo==2 else False
            data['estudiante'] = inscripcion.persona
            data['archivos'] = ArchivoTitulacion.objects.filter(vigente=True, status=True).distinct()
            # lista = PropuestaTitulacion.objects.values_list("matricula").filter(Q(matricula__alternativa__carrera=inscripcion.carrera), Q(matricula__alternativa_id=matricula.alternativa.id),(Q(estado=1) | Q(estado=2)))
            data['add'] = True
            if PropuestaTitulacion_Matricula.objects.filter(matricula=matricula,status=True, matricula__estado=7).exists() :
                data['add']= False
            if matricula.alternativa.tipotitulacion.tipo==2:
                return HttpResponseRedirect("/alu_complexivocurso")
            else:
                return render(request, "alu_propuestatitulacion/view.html", data)
            # return render(request, "alu_propuestatitulacion/view.html", data)
