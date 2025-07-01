# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.models import datetime, Banco
from sga.commonviews import adduserdata
from sga.forms import EliminarInscripcionActividadForm, ReemplazarInformeActividadExtracurricularForm, InstitucionActividadPPVForm
from sga.funciones import MiPaginador, log, cuenta_email_disponible, remover_caracteres_especiales_unicode, \
    generar_nombre, variable_valor
from sga.models import ActividadConvalidacionPPV, InscripcionActividadConvalidacionPPV, miinstitucion, CUENTAS_CORREOS, \
    PreInscripcionPracticasPP, InscripcionRequisitosActividadConvalidacionPPV, DetallePreInscripcionPracticasPP
from django.template import Context
from django.template.loader import get_template
import time as ET

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@last_access
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")

    inscripcion = perfilprincipal.inscripcion

    if inscripcion.graduado():
        return HttpResponseRedirect("/?info=Ingreso no permitido a graduados.")

    if not inscripcion.inscripcionmalla_set.filter(status=True):
        return HttpResponseRedirect("/?info=Debe tener malla asociada para poder inscribirse a una actividad extracurricular.")

    # if inscripcion.practicaspreprofesionalesinscripcion_set.all():
    #     return HttpResponseRedirect("/?info=No permitido a alumnos preinscritos en Practicas PreProfesionales.")
    serviciocomunitario_carreras = variable_valor('VARIOS_SERVICIOCOMUNITARIO_CARRERAS')
    practica_carreras = variable_valor('VARIOS_PRACTICA_CARRERAS')
    data['permite_varios_servicio'] = permite_varios_servicio = str(inscripcion.carrera.id) in serviciocomunitario_carreras if serviciocomunitario_carreras else False
    data['permite_varios_practica'] = permite_varios_practica = str(inscripcion.carrera.id) in practica_carreras if practica_carreras else False

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'inscribir':
            try:
                actividad = ActividadConvalidacionPPV.objects.get(pk=request.POST['id'])
                selecciona_varios = False
                if actividad.tipoactividad == 1: selecciona_varios = permite_varios_practica
                else: selecciona_varios = permite_varios_servicio

                if not actividad.en_fecha_inscripcion():
                    return JsonResponse({"result": "bad", "mensaje": u"El periodo de inscripción ha finalizado"})

                if actividad.alumno_inscrito_actividad(inscripcion):
                    return JsonResponse({"result": "bad", "mensaje": u"Usted ya está inscrito en la actividad seleccionada"})

                if actividad.total_cupo_disponible() < 1:
                    return JsonResponse({"result": "bad", "mensaje": u"No existen cupos disponibles para inscribirse en la actividad seleccionada"})

                if actividad.alumno_inscrito_itinerario():
                    return JsonResponse({"result": "bad", "mensaje": u"Usted ya tiene una actividad con el mismo itinerario aprobada"})

                if InscripcionActividadConvalidacionPPV.objects.values_list('actividad_id').filter(status=True,
                                                                                                inscripcion=inscripcion,
                                                                                                estado__in=[1, 2, 4],
                                                                                                   actividad=actividad).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Usted ya tiene una inscripcion en una actividad del mismo tipo"})

                if not selecciona_varios and InscripcionActividadConvalidacionPPV.objects.filter(status=True, inscripcion=inscripcion, actividad__periodo_id= periodo, estado__in=[1, 2, 4]):
                    return JsonResponse({"result": "bad", "mensaje": u"Usted ya tiene una inscripción en este periodo"})

                inscripcion = InscripcionActividadConvalidacionPPV(actividad=actividad,
                                                                   inscripcion=inscripcion,
                                                                   estado=1)
                inscripcion.save(request)

                log(u'%s agregó inscripción en la actividad de convalidación PPV: %s' % (persona, actividad), request,"add")

                # Envío de correo al estudiante
                cuenta = cuenta_email_disponible()
                tituloemail = "Inscripción Actividad Extracurricular"
                estudiante = persona
                saludo = 'Estimado(a)'
                if estudiante.sexo:
                    saludo='Estimada' if estudiante.sexo.id == 1 else 'Estimado',

                send_html_mail(tituloemail,
                               "emails/inscripcionactividadppv.html",
                               {'sistema': u'SGA - UNEMI',
                                'accion': 'INSCRIPCION',
                                'fecha': datetime.now().date(),
                                'hora': datetime.now().time(),
                                'saludo': saludo,
                                'estudiante': estudiante,
                                'actividad': actividad.titulo,
                                'periodo': actividad.periodo.nombre,
                                't': miinstitucion()
                                },
                               estudiante.lista_emails_envio(),
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicion de gmail
                # ET.sleep(5)

                # Envío de correo al profesor líder para que acepte o rechace la inscripción
                cuenta = cuenta_email_disponible()
                tituloemail = "Inscripción de Estudiante a Actividad Extracurricular"
                docente = actividad.profesor.persona

                send_html_mail(tituloemail,
                               "emails/inscripcionactividadppv.html",
                               {'sistema': u'SGA - UNEMI',
                                'accion': 'NOTIFICADOCENTE',
                                'fecha': datetime.now().date(),
                                'hora': datetime.now().time(),
                                'saludo': saludo,
                                'docente': docente,
                                'estudiante': estudiante,
                                'actividad': actividad.titulo,
                                'periodo': actividad.periodo.nombre,
                                't': miinstitucion()
                                },
                               docente.lista_emails_envio(),
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicion de gmail
                # ET.sleep(5)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'eliminarinscripcion':
            try:
                persona = request.session['persona']
                idinscripcion = int(request.POST['id'])
                inscripcion = InscripcionActividadConvalidacionPPV.objects.get(pk=idinscripcion)

                if inscripcion.estadoprofesor:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar debido a que el profesor asignó el estado %s." % (inscripcion.get_estadoprofesor_display())})

                f = EliminarInscripcionActividadForm(request.POST)
                if f.is_valid():
                    inscripcion.estado = 5
                    inscripcion.status = False
                    inscripcion.observacion = f.cleaned_data['observacion'].strip().upper()
                    inscripcion.save(request)

                    log(u'%s eliminó la inscripción a la actividad %s' % (persona, inscripcion), request, "edit")

                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')

            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        # elif action == 'addinscritomanual':
        #     try:
        #         id = request.POST['id']
        #         idinscripcion = InscripcionActividadConvalidacionPPV.objects.get(pk=id)
        #
        #         f = ReemplazarInformeActividadExtracurricularForm(request.POST)
        #         if f.is_valid():
        #             newfile = request.FILES['archivo']
        #             extension = newfile._name.split('.')
        #             tam = len(extension)
        #             exte = extension[tam - 1]
        #             if newfile.size > 4194304:
        #                 transaction.set_rollback(True)
        #                 return JsonResponse(
        #                     {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
        #             if not exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
        #                 transaction.set_rollback(True)
        #                 return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
        #             nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
        #             newfile._name = generar_nombre("{}__{}".format(nombre_persona, instance.requisito.nombre_input()),
        #                                            newfile._name)
        #             instance.archivo = newfile
        #             instance.estado = 0
        #             instance.save(request)
        #             log(u'Documento Requisito Solicitud %s' % (instance), request, "add")
        #             return JsonResponse({"result": True})
        #         else:
        #             transaction.set_rollback(True)
        #             return JsonResponse({"result": True})
        #         # return JsonResponse({"result": True})
        #     except Exception as ex:
        #         return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'addinstitucion':
            try:
                inscri = InscripcionActividadConvalidacionPPV.objects.get(pk=request.POST['id'])
                form = InstitucionActividadPPVForm(request.POST, request.FILES)

                if form.is_valid():
                    descrip = str(form.cleaned_data['institucion'])
                    if descrip == '':
                        return JsonResponse({"result": True, "mensaje": "Llene el campo institución."}, safe=False)

                    inscri.institucion_actividad = descrip
                    inscri.save(request)

                    return JsonResponse({'result': False})
            except Exception as ex:
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)


        elif action == 'reemplazardocumento':
            try:
                instance = InscripcionRequisitosActividadConvalidacionPPV.objects.get(id=int(request.POST['id']))
                f = ReemplazarInformeActividadExtracurricularForm(request.POST)
                mensaje = "Complete los datos requeridos."
                if f.is_valid():
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 4194304:
                        mensaje = 'El tamaño del archivo es mayor a 4 Mb.'
                        raise NameError(mensaje)
                    if not exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                        mensaje = 'Solo archivos .pdf,.jpg, .jpeg'
                        raise NameError(mensaje)
                    nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
                    newfile._name = generar_nombre("{}__{}_{}".format(nombre_persona, 'archivo_evidencia', instance.id), newfile._name)
                    instance.archivo = newfile
                    instance.estado = 0
                    instance.save(request)
                    log(u'Documento Requisito Solicitud %s' % (instance), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                raise NameError(mensaje)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)}, safe=False)
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'inscribir':
                try:
                    data['title'] = u'Inscribirse a la Actividad ExtraCurricular'
                    data['actividad'] = ActividadConvalidacionPPV.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_convalidacionpractica/inscripcionactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'eliminarinscripcion':
                try:
                    data['title'] = u'Eliminar Inscripción a Actividad Extracurricular'
                    data['id'] = int(request.GET['id'])
                    data['inscripcion'] = InscripcionActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))

                    form = EliminarInscripcionActividadForm()

                    template = get_template("alu_convalidacionpractica/eliminainscripcion.html")
                    data['form'] = form
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'addinstitucion':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = InscripcionActividadConvalidacionPPV.objects.get(pk=id)
                    form = InstitucionActividadPPVForm()
                    data['form2'] = form
                    template = get_template("alu_convalidacionpractica/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listadoactividades':
                try:
                    data['prcaticas_en_proceso'] = prcaticas_en_proceso = DetallePreInscripcionPracticasPP.objects.filter(status=True, inscripcion=inscripcion, estado__in=[1, 2, 4, 6]).values('id').exists() and not permite_varios_practica
                    data['actividad_en_proceso'] = actividad_en_proceso = InscripcionActividadConvalidacionPPV.objects.filter(status=True,estado__in=[1,2,4],inscripcion=inscripcion).exists() and not permite_varios_servicio
                    # if DetallePreInscripcionPracticasPP.objects.filter(status=True, inscripcion=inscripcion, estado__in=[1,2,4,6]).values('id').exists():
                    #     return HttpResponseRedirect("/alu_convalidacionpractica?info=Usted ya se encuetra pre inscrito en practicas pre profesionales.")
                    # if InscripcionActividadConvalidacionPPV.objects.values_list('actividad_id').filter(status=True, inscripcion=inscripcion , estado__in=[1,2,4,6]).exists():
                    #     return HttpResponseRedirect("/alu_convalidacionpractica?info=Usted ya tiene una actividad en curso.")
                    data['title'] = u'Actividades Extracurriculares de Convalidación de Prácticas Preprofesionales y Proyectos de Servicio Comunitario'

                    puedepractica = inscripcion.puede_inscribirse_actividad_extracurricularconvalidacion_practica()['puedeinscribir']
                    puedevinculacion = inscripcion.puede_inscribirse_actividad_extracurricularconvalidacion_vinculacion()['puedeinscribir']

                    mis_actividades = InscripcionActividadConvalidacionPPV.objects.values_list('actividad_id').filter(status=True, inscripcion=inscripcion)

                    search = None
                    ids = None
                    actividades = []
                    actividades1 = actividades2 = None

                    # validaciones de nivel itinerario

                    itinerarios = []

                    if inscripcion.inscripcionmalla_set.filter(status=True).values('id').exists():
                        if inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True).exists():
                            matricula = inscripcion.matricula_set.filter(status=True)[0]
                            listaitinerariorealizado = inscripcion.cumple_total_horas_itinerario()
                            itinerariosvalidosid = []
                            for it in inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True):
                                nivelhasta = it.nivel.orden
                                if inscripcion.todas_materias_aprobadas_rango_nivel(1, nivelhasta):
                                    itinerariosvalidosid.append(it.pk)
                            itinerarios = inscripcion.inscripcionmalla_set.filter(status=True)[
                                0].malla.itinerariosmalla_set.values_list(
                                'id', flat=True).filter(status=True).filter(pk__in=itinerariosvalidosid).exclude(
                                id__in=listaitinerariorealizado)

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        # if puedepractica and not prcaticas_en_proceso:
                        actividades1 = ActividadConvalidacionPPV.objects.filter(titulo__icontains=search, status=True,
                                                                                tipoactividad=1,
                                                                                detalleactividadconvalidacionppv__isnull=False,
                                                                                inicioinscripcion__lte=datetime.now().date(),
                                                                                fininscripcion__gte=datetime.now().date(),
                                                                                carrera=inscripcion.carrera).exclude(pk__in=mis_actividades).distinct().order_by('-id')
                        if len(itinerarios) > 1:
                            actividades1 = actividades1.filter(itinerariomalla_id__in=itinerarios).order_by('-id')
                        # if puedevinculacion and not actividad_en_proceso:
                        actividades2 = ActividadConvalidacionPPV.objects.filter(titulo__icontains=search, status=True,
                                                                                    tipoactividad=2,
                                                                                    detalleactividadconvalidacionppv__isnull=False,
                                                                                    inicioinscripcion__lte=datetime.now().date(),
                                                                                    fininscripcion__gte=datetime.now().date(),
                                                                                    carrera=inscripcion.carrera).exclude(pk__in=mis_actividades).distinct().order_by('-id')

                        if actividades1 and actividades2:
                            actividades = actividades1|actividades2
                        else:
                            actividades = actividades1 if actividades1 else actividades2 if actividades2 else ActividadConvalidacionPPV.objects.none()

                        # actividades = actividades.order_by('-id')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        actividades = ActividadConvalidacionPPV.objects.filter(id=ids, status=True,
                                                                               periodo=periodo).order_by('-id')
                    else:
                        # if puedepractica and not prcaticas_en_proceso:
                        actividades1 = ActividadConvalidacionPPV.objects.filter(status=True, tipoactividad=1, detalleactividadconvalidacionppv__isnull=False, inicioinscripcion__lte=datetime.now().date(), fininscripcion__gte=datetime.now().date(), carrera=inscripcion.carrera).exclude(pk__in=mis_actividades).distinct().order_by('-id')
                        if len(itinerarios) > 1:
                            actividades1 = actividades1.filter(itinerariomalla_id__in=itinerarios).order_by('-id')
                        # if puedevinculacion and not actividad_en_proceso:
                        actividades2 = ActividadConvalidacionPPV.objects.filter(status=True, tipoactividad=2, detalleactividadconvalidacionppv__isnull=False, inicioinscripcion__lte=datetime.now().date(), fininscripcion__gte=datetime.now().date(), carrera=inscripcion.carrera).exclude(pk__in=mis_actividades).distinct().order_by('-id')

                        if actividades1 and actividades2:
                            actividades = actividades1 | actividades2
                        else:
                            actividades = actividades1 if actividades1 else actividades2 if actividades2 else ActividadConvalidacionPPV.objects.none()


                    paging = MiPaginador(actividades, 25)
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
                    data['actividades'] = page.object_list
                    data['puedeinscribir'] = puedevinculacion or puedepractica
                    data['inscripcion'] = inscripcion
                    data['mensaje'] = "Estimado estudiante usted no cumple con los requisitos para poder inscribirse a una actividad extracurricular de convalidación"

                    return render(request, "alu_convalidacionpractica/listadoactividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrararchivos':
                try:
                    data['title'] = u'Archivos Soporte de la Actividad Extracurricular'
                    data['id'] = int(request.GET['id'])
                    data['actividad'] = ActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))

                    template = get_template("adm_convalidacionpractica/mostrararchivoactividad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'cargarinformes':
                try:
                    data ['fechaactual'] = fechaactual = datetime.now().date()
                    data['title'] = u'Informes Actividad Extracurricular'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = InscripcionActividadConvalidacionPPV.objects.get(pk=id)
                    for req in filtro.actividad.requisitosactividad():
                        if not InscripcionRequisitosActividadConvalidacionPPV.objects.filter(status=True, actividad=filtro, requisito=req).exists():
                            requisito = InscripcionRequisitosActividadConvalidacionPPV(actividad=filtro, requisito=req)
                            requisito.save(request)
                    excluidos = InscripcionRequisitosActividadConvalidacionPPV.objects.filter(status=True, actividad=filtro).exclude(requisito__in=filtro.actividad.requisitosactividad().values_list('id',flat=True))
                    for e in excluidos:
                        e.status = False
                        e.save(request)
                    return render(request, 'alu_convalidacionpractica/requisitos.html', data)
                except Exception as ex:
                    pass

            elif action == 'reemplazardocumento':
                try:
                    data['filtro'] = solicitud = InscripcionRequisitosActividadConvalidacionPPV.objects.get(pk=int(request.GET['id']))
                    form = ReemplazarInformeActividadExtracurricularForm(initial=model_to_dict(solicitud))
                    data['form2'] = form
                    #solicitud.estado = 0
                    template = get_template("alu_convalidacionpractica/reemplazardocumento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

        else:
            data['title'] = u'Mis Actividades Extracurriculares de Convalidación de Prácticas Preprofesionales y Proyectos de Servicio Comunitario'

            search = None
            ids = None

            if 's' in request.GET:
                search = request.GET['s'].strip()
                inscripciones = InscripcionActividadConvalidacionPPV.objects.filter(status=True,
                                                                                    actividad__status=True,
                                                                                    actividad__titulo__icontains=search,
                                                                                    inscripcion=inscripcion).order_by('-id')
            else:
                inscripciones = InscripcionActividadConvalidacionPPV.objects.filter(status=True,
                                                                                    actividad__status=True,
                                                                                    inscripcion=inscripcion).order_by('-id')

            validacion = inscripcion.puede_inscribirse_actividad_extracurricularconvalidacion_practica()
            validacion2 = inscripcion.puede_inscribirse_actividad_extracurricularconvalidacion_vinculacion()

            puedeinscribir = validacion['puedeinscribir'] or validacion2['puedeinscribir']

            paging = MiPaginador(inscripciones, 25)
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
            data['inscripciones'] = page.object_list
            data['puedeinscribir'] = puedeinscribir
            data['inscripcion'] = inscripcion
            data['mensaje'] = "Estimado estudiante usted no cumple con los requisitos para poder inscribirse a una actividad extracurricular de convalidación"

            return render(request, "alu_convalidacionpractica/view.html", data)