# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import SolicitudTutorForm, SolicitudTutorVerRespuestaForm,SolicitudTutorMateriaForm
from sga.funciones import MiPaginador, log, puede_realizar_accion, variable_valor,generar_nombre
from sga.models import SolicitudTutorSoporteMatricula, Materia, SolicitudTutorSoporteMateria, MateriaAsignada, \
    RespuestaSolicitudTutorSoporteMateria, Notificacion
from sga.templatetags.sga_extras import encrypt
from django.db.models import Q

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if not request.session['periodo']:
        return HttpResponseRedirect("/?info=No tiene periodo asignado.")
    data['periodo'] =periodo= request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['insccripcion'] =inscripcion = perfilprincipal.inscripcion
    matricula = inscripcion.matricula_periodo(periodo)
    data['cordinacionid']=cordinacionid = inscripcion.carrera.coordinacion_carrera().id
    if cordinacionid in [9]:
        return HttpResponseRedirect(
            "/?info=Estimado aspirante, este módulo esta habilitado solo para estudiantes de pregrado")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                form = SolicitudTutorForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if exte.lower() == 'pdf' or exte.lower() == 'jpg' or exte.lower() == 'jpeg':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})

                if form.is_valid():
                    archivo = None
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = generar_nombre("solicitud", archivo._name)
                    solicitud = SolicitudTutorSoporteMatricula(matricula=matricula,
                                                               descripcion=form.cleaned_data['descripcion'],
                                                               tipo=form.cleaned_data['tipo'],
                                                               archivo=archivo)
                    solicitud.save(request)
                    log(u'Adicionó solicitud de tutor: %s' % solicitud, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'editsolicitud':
            try:
                form = SolicitudTutorForm(request.POST, request.FILES)
                solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.POST['id'])))

                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if exte.lower() == 'pdf' or exte.lower() == 'jpg' or exte.lower() == 'jpeg':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})

                if form.is_valid():
                    solicitud.tipo = form.cleaned_data['tipo']
                    solicitud.descripcion = form.cleaned_data['descripcion']
                    solicitud.save(request)
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = generar_nombre("solicitud", archivo._name)
                        solicitud.archivo = archivo
                    solicitud.save(request)
                    log(u'Editó solicitud de tutor: %s' % solicitud, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'verrespuesta':
            try:
                form = SolicitudTutorVerRespuestaForm(request.POST)
                solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    respuesta = solicitud.respuestasolicitudtutorsoportematricula_set.filter(status=True).order_by('-id')[0]
                    atendido = False
                    if int(form.cleaned_data['atendida']) == 1:
                        atendido = True
                    if not atendido:
                        solicitud.estado = 4
                        solicitud.save(request)
                    respuesta.atendida = atendido
                    respuesta.respuesta = form.cleaned_data['respuestaestudiante']
                    respuesta.save(request)
                    log(u'Ingreso respuesta estudiante solicitud: %s' % respuesta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'delsolicitud':
            try:
                solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=request.POST['id'])
                log(u'Eliminó solicitud de tutor: %s' % (solicitud), request, "del")
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. Detalle: %s" % (msg)})

        elif action == 'verobservaciones':
            try:
                id = int(request.POST['id'])
                solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=id)
                data['solicitud'] = solicitud
                data['respuestas_tutor'] = respuesta = solicitud.respuestasolicitudtutorsoportematricula_set.filter(status=True).order_by('id')
                data['observaciones_tutor'] = solicitud.observacionsolicitudtutorsoportematricula_set.filter(status=True).order_by('-id')
                data['atendido'] = ''
                data['respuestas_estudiante'] = ''
                if respuesta:
                    data['atendido'] = respuesta[0].atendida
                    data['respuestas_estudiante'] = respuesta[0].respuesta
                template = get_template("alu_solicitudtutor/verobservaciones.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'buscarprofesor':
            try:
                from sga.models import ProfesorDistributivoHoras
                materia = Materia.objects.get(pk=request.POST['id'])
                lista = []
                # for profesormateria in materia.profesormateria_set.filter(status=True,activo=True,tipoprofesor_id__in=[8]):
                if request.session['coordinacion'] == 7:
                    for profesormateria in materia.profesormateria_set.filter(status=True, activo=True, tipoprofesor_id__in=[8]):
                        lista.append([profesormateria.profesor.id, profesormateria.profesor.persona.nombre_completo_inverso()])
                else:
                    docentes = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo,
                                                                        detalledistributivo__criteriodocenciaperiodo__criterio_id=136, profesor__persona__real=True).values_list('profesor_id', flat=True).distinct()
                    for profesormateria in materia.profesormateria_set.filter(status=True, activo=True, profesor_id__in=docentes):
                        lista.append([profesormateria.profesor.id, profesormateria.profesor.persona.nombre_completo_inverso()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addsolicitudtutormateria':
            try:
                form = SolicitudTutorMateriaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if exte.lower() == 'pdf' or exte.lower() == 'jpg' or exte.lower() == 'jpeg':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})

                archivo = None
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    archivo._name = generar_nombre("solicitudtutormateria", archivo._name)

                materiaasignada = MateriaAsignada.objects.get(materia=request.POST['materia'], matricula=matricula,
                                                             retiramateria=False)
                solicitud = SolicitudTutorSoporteMateria(materiaasignada=materiaasignada,
                                                         profesor_id=int(request.POST['profesor']),
                                                           descripcion=request.POST['descripcion'],
                                                           tipo=int(request.POST['tipo']),
                                                           archivo=archivo)
                solicitud.save(request)
                log(u'Adicionó solicitud a tutor de su materia: %s' % materiaasignada, request, "add")

                # Notificacion para el docente
                notificacion = Notificacion(
                    titulo='Consulta de acompañamiento del alumno %s' % solicitud.materiaasignada.matricula.inscripcion.persona.nombre_completo_minus(),
                    cuerpo='Tiene una consulta de la asignatura %s' % solicitud.materiaasignada.materia.asignatura,
                    destinatario=solicitud.profesor.persona,
                    url="/pro_tutoria?action=verobservacionesmimateria&id={}".format(solicitud.pk),
                    content_type=None,
                    object_id=solicitud.pk,
                    prioridad=2,
                    fecha_hora_visible=datetime.now() + timedelta(days=1),
                    app_label='sga',
                )
                notificacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'editsolicitudtutormateria':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if exte.lower() == 'pdf' or exte.lower() == 'jpg' or exte.lower() == 'jpeg':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})

                archivo = None
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    archivo._name = generar_nombre("solicitudtutormateria", archivo._name)

                materiaasignada = MateriaAsignada.objects.get(materia=request.POST['materia'], matricula=matricula, retiramateria=False)
                solicitud = SolicitudTutorSoporteMateria.objects.get(id=int(encrypt(request.POST['id'])))
                solicitud.materiaasignada=materiaasignada
                solicitud.profesor_id=int(request.POST['profesor'])
                solicitud.descripcion=request.POST['descripcion']
                solicitud.tipo=int(request.POST['tipo'])
                if archivo:
                    solicitud.archivo=archivo
                solicitud.save(request)
                log(u'Editó solicitud a tutor de su materia: %s' % materiaasignada, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'delsolicitudtutormateria':
            try:
                solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.POST['id'])))
                if not solicitud.en_uso():
                    solicitud.status=False
                    solicitud.save(request)
                    log(u'Eliminó solicitud de tutoria academica: %s' % solicitud, request, "del")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error la solicitud ya esta programada."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'verobservacionesmimateria':
            try:
                data['solicitud'] =solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(request.POST['id']))
                data['respuestas_tutor'] = respuesta = solicitud.respuestasolicitudtutorsoportemateria_set.filter(status=True).order_by('id')
                data['observaciones_tutor'] = solicitud.observacionsolicitudtutorsoportemateria_set.filter(status=True).order_by('-id')
                data['atendido'] = ''
                data['respuestas_estudiante'] = ''
                if respuesta:
                    data['atendido'] = respuesta[0].atendida
                    data['respuestas_estudiante'] = respuesta[0].respuesta
                template = get_template("alu_solicitudtutor/verobservacionesmimateria.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'verrespuestamateria':
            try:
                form = SolicitudTutorVerRespuestaForm(request.POST)
                solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    respuesta = solicitud.respuestasolicitudtutorsoportemateria_set.filter(status=True).order_by('-id')[0]
                    atendido = False
                    if int(form.cleaned_data['atendida']) == 1:
                        atendido = True
                    if not atendido:
                        solicitud.estado = 4
                        solicitud.save(request)
                    respuesta.atendida = atendido
                    respuesta.respuesta = form.cleaned_data['respuestaestudiante']
                    respuesta.save(request)
                    log(u'Ingreso respuesta estudiante solicitud: %s' % respuesta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'respuestaalumno':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    exte = exte.lower()

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte == 'pdf' and not exte == 'jpg' and not exte == 'jpeg' and not exte == 'png':
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})

                # respuesta = RespuestaSolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.POST['id'])))
                # solicitud = respuesta.solicitud
                solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.POST['id'])))
                respuesta = solicitud.respuestas().last()

                archivo = None
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    archivo._name = generar_nombre("respondersolicitudmimateria", archivo._name)

                respuesta.respuesta = request.POST['respuesta']
                respuesta.archivoalu = archivo
                respuesta.fecharespuesta = datetime.now()
                respuesta.save(request)
                atendido = False
                # if int(request.POST['atendida']) == 1:
                #     atendido = True
                #     solicitud.estado = 3
                # if not atendido:
                #     solicitud.estado = 4
                #     solicitud.save(request)
                log(u'Ingreso respuesta estudiante solicitud: %s' % respuesta, request, "edit")
                # Notificacion para el docente
                notificacion = Notificacion(
                    titulo='Respuesta de alumno %s' % solicitud.materiaasignada.matricula.inscripcion.persona.nombre_completo_minus(),
                    cuerpo='Tiene una respuesta de la asignatura %s' % solicitud.materiaasignada.materia,
                    destinatario=solicitud.profesor.persona,
                    url="/pro_tutoria?action=verobservacionesmimateria&id={}".format(solicitud.pk),
                    content_type=None,
                    object_id=respuesta.pk,
                    prioridad=2,
                    fecha_hora_visible=datetime.now() + timedelta(days=1),
                    app_label='sga',
                    )
                notificacion.save(request)
                return JsonResponse({"result": "ok", 'mensaje': 'Respuesta enviada correctamente', 'id': request.POST['id']})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", 'mensaje':'Error en la transaccion '+str(e)})

        elif action == 'estadosolicitud':
            try:
                solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.POST['id'])))
                estado = request.POST['atendida'] if 'atendida' in request.POST else False
                solicitud.estado = 3 if estado else 2
                solicitud.save(request)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "{}".format(ex)})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Agregar Solicitud'
                    form = SolicitudTutorForm()
                    data['form'] = form
                    return render(request, "alu_solicitudtutor/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar Solicitud'
                    solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = SolicitudTutorForm(initial={'tipo': solicitud.tipo,
                                                       'descripcion': solicitud.descripcion})
                    data['idsolicitud'] = solicitud.id
                    data['form'] = form
                    return render(request, "alu_solicitudtutor/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'verrespuesta':
                try:
                    data['title'] = u'Respuesta Solicitud'
                    solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    respuesta = solicitud.respuestasolicitudtutorsoportematricula_set.filter(status=True).order_by('id')[0]
                    form = SolicitudTutorVerRespuestaForm(initial={'tipo': solicitud.tipo,
                                                                   'descripcion': solicitud.descripcion,
                                                                   'respuesta': respuesta.descripcion})
                    data['idsolicitud'] = solicitud.id
                    form.respuestas()
                    data['form'] = form
                    return render(request, "alu_solicitudtutor/verrespuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar Solicitud'
                    data['solicitud'] = solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_solicitudtutor/deletesolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitudestutormateria':
                try:
                    if inscripcion.carrera.modalidad in [1, 2, 3]:
                        data['title'] = u'Solicitudes al tutor de mis materias'
                        search = None
                        ids = None
                        solicitudes = SolicitudTutorSoporteMateria.objects.filter(materiaasignada__matricula=matricula, status=True)
                        if 's' in request.GET:
                            search = request.GET['s']
                        if search:
                            solicitudes = solicitudes.filter(
                            Q(materiaasignada__materia__asignatura__nombre__icontains=search) |
                            Q(materiaasignada__materia__paralelomateria__nombre__icontains=search))
                        elif 'id' in request.GET:
                            ids = request.GET['id']
                            solicitudes = solicitudes.filter(id=ids)
                        paging = MiPaginador(solicitudes, 20)
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
                        data['solicitudes'] = page.object_list
                        return render(request, "alu_solicitudtutor/solicitudestutormateria.html", data)
                    else:
                        return HttpResponseRedirect("/alu_solicitudtutor")
                except Exception as ex:
                    pass

            elif action == 'addsolicitudtutormateria':
                try:
                    data['title'] = u'Agregar solicitud'
                    form = SolicitudTutorMateriaForm()
                    form.iniciar(periodo,matricula)
                    data['form'] = form
                    data['action'] = action
                    return render(request, "alu_solicitudtutor/addsolicitudtutormateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitudtutormateria':
                try:
                    data['title'] = u'Editar Solicitud'
                    data['solicitud'] = solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = SolicitudTutorMateriaForm(initial={'materia':solicitud.materiaasignada.materia,
                                                                   'profesor':solicitud.profesor,
                                                                   'tipo':solicitud.tipo,
                                                                   'descripcion':solicitud.descripcion})
                    form.editar(periodo, matricula,solicitud)
                    data['form'] = form
                    data['archivo'] = solicitud.archivo.url if solicitud.archivo else None
                    data['action'] = action
                    return render(request, "alu_solicitudtutor/addsolicitudtutormateria.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delsolicitudtutormateria':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitud'] = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_solicitudtutor/delsolicitudtutormateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'verrespuestamateria':
                try:
                    data['title'] = u'Respuesta solicitud'
                    data['solicitud'] = solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.GET['id'])))
                    respuesta = solicitud.respuestasolicitudtutorsoportemateria_set.filter(status=True).order_by('id')[0]
                    form = SolicitudTutorVerRespuestaForm(initial={'tipo': solicitud.tipo,
                                                                   'descripcion': solicitud.descripcion,
                                                                   'respuesta': respuesta.descripcion,
                                                                   'respuestaestudiante':respuesta.respuesta})
                    form.respuestas()
                    data['form'] = form
                    return render(request, "alu_solicitudtutor/verrespuestamateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionrespuestas':
                try:
                    data['solicitud'] = solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(request.GET['id']))
                    data['title'] = 'Gestion de respuestas de seguimiento acádemico'
                    data['form'] = SolicitudTutorVerRespuestaForm()
                    return render(request, "alu_solicitudtutor/gestionrespuestasalumno.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                solicitudes = SolicitudTutorSoporteMatricula.objects.filter(matricula=matricula, status=True).order_by('-id')
                data['title'] = 'Listado de Solicitudes'
                data['solicitudes'] = solicitudes
                # if inscripcion.carrera.modalidad in [1,2]:
                if cordinacionid == 7:
                    return render(request, "alu_solicitudtutor/view.html", data)
                return HttpResponseRedirect("/alu_solicitudtutor?action=solicitudestutormateria")
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})