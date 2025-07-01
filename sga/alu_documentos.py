# -*- coding: latin-1 -*-
import sys
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q

from matricula.models import PeriodoMatricula
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from decorators import secure_module, last_access
from django.template.loader import get_template
from settings import USA_PLANIFICACION
from sga.commonviews import adduserdata
from sga.forms import ArchivoPlanificacionForm, AvPreguntaDocenteForm
from sga.funciones import generar_nombre, log, variable_valor, MiPaginador
from sga.models import Materia, Leccion, MateriaAsignada, MateriaAsignadaPlanificacion, AvPreguntaDocente, \
    AvPreguntaRespuesta, Silabo, InscripcionMalla, LibroKohaProgramaAnaliticoAsignatura, \
    DetalleSilaboSemanalBibliografiaDocente, GPGuiaPracticaSemanal, SesionZoom, Matricula,HorarioExamen,DetalleSesionZoom
from sga.templatetags.sga_extras import encrypt_alu
from sga.commonviews import get_client_ip

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion

    if periodo is None:
        return HttpResponseRedirect("/")

    # automatricula de pregrado
    confirmar_automatricula_pregrado = inscripcion.tiene_automatriculapregrado_por_confirmar(periodo)
    if confirmar_automatricula_pregrado:
        mat = inscripcion.mi_matricula_periodo(periodo.id)
        if mat.nivel.fechainicioagregacion > datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado estudiante, se informa que el proceso de aceptación de matrícula empieza %s" % mat.nivel.fechainicioagregacion.__str__())
        if mat.nivel.fechafinagregacion < datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado estudiante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
        if PeriodoMatricula.objects.values("id").filter(periodo=periodo, status=True).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=periodo, status=True)[0]
            if not ePeriodoMatricula.activo:
                return HttpResponseRedirect("/?info=Estimado aspirante, se informa que el proceso de matrícula se encuentra inactivo")
        return HttpResponseRedirect("/alu_matricula/pregrado")

    # automatricula de admisión
    confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
    if confirmar_automatricula_admision:
        mat = inscripcion.mi_matricula_periodo(periodo.id)
        if mat.nivel.fechainicioagregacion > datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado aspirante, se informa que el proceso de aceptación de matrícula empieza %s" % mat.nivel.fechainicioagregacion.__str__())
        if mat.nivel.fechafinagregacion < datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
        if PeriodoMatricula.objects.values("id").filter(periodo=periodo, status=True).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=periodo, status=True)[0]
            if not ePeriodoMatricula.activo:
                return HttpResponseRedirect("/?info=Estimado estudiante, se informa que el proceso de matrícula se encuentra inactivo")
        return HttpResponseRedirect("/alu_matricula/admision")

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'subirdeberplanificacion':
                try:
                    miplanificacion = MateriaAsignadaPlanificacion.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                    if not miplanificacion.planificacion.en_fecha():
                        mensaje = u"Fecha y Hora subida = %s %s, Fecha y Hora Máxima de entrega = %s %s, Materia: %s." % (datetime.now().date().strftime('%Y-%m-%d'), datetime.now().time().strftime("%H:%M %p"), miplanificacion.planificacion.hasta, miplanificacion.planificacion.horahasta, miplanificacion.materiaasignada.materia)
                        log(u'Notificación Deber: tiempo de entrega a caducado: %s' % mensaje, request, "add")
                        return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos el tiempo de entrega a caducado: %s" % mensaje})
                    form = ArchivoPlanificacionForm(request.POST, request.FILES)
                    d = request.FILES['archivo']
                    if d.size > 5194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                    if form.is_valid():
                        tarea = request.FILES['archivo']
                        nameoriginal = tarea._name
                        tarea._name = generar_nombre("tarea_", tarea._name)
                        miplanificacion.archivo = tarea
                        miplanificacion.fechaentrega = datetime.now().date()
                        miplanificacion.horaentrega = datetime.now().time()
                        miplanificacion.save(request)
                        log(u'Alumno subio Deber: %s, Archivo original: %s - Archivo sistema:%s' % (miplanificacion, nameoriginal, tarea._name), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'deldeberplanificacion':
                try:
                    miplanificacion = MateriaAsignadaPlanificacion.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                    if not miplanificacion.calificacion:
                        deber = miplanificacion.archivo
                        miplanificacion.archivo = None
                        miplanificacion.fechaentrega = None
                        miplanificacion.horaentrega = None
                        miplanificacion.save(request)
                        log(u'Alumno elimino Deber: %s, Nombre del archivo eliminado:%s' % (miplanificacion, deber), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        JsonResponse({"result": "bad", "mensaje": u"Tarea no puede ser eliminada, porque se encuentra calificada."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'crearpregunta':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=encrypt_alu(request.POST['id']))
                    form = AvPreguntaDocenteForm(request.POST, request.FILES)
                    if form.is_valid():
                        avpreguntadocente = AvPreguntaDocente(materiaasignada=materiaasignada,
                                                              profersormateria=form.cleaned_data['profersormateria'],
                                                              tema=form.cleaned_data['tema'],
                                                              pregunta=form.cleaned_data['pregunta'],
                                                              estadolectura=True,
                                                              estadolecturaalumno=False)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("pregunta", newfile._name)
                                avpreguntadocente.archivo = newfile
                        avpreguntadocente.save(request)
                        log(u'Alumno ingreso pregunta:%s' % avpreguntadocente, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editpregunta':
                try:
                    form = AvPreguntaDocenteForm(request.POST, request.FILES)
                    if form.is_valid():
                        avpreguntadocente = AvPreguntaDocente.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                        avpreguntadocente.tema = form.cleaned_data['tema']
                        avpreguntadocente.pregunta = form.cleaned_data['pregunta']
                        avpreguntadocente.estadolectura = True
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("pregunta", newfile._name)
                                avpreguntadocente.archivo = newfile
                        avpreguntadocente.save(request)
                        log(u'Alumno modifico pregunta:%s' % avpreguntadocente, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'deleteconversacion':
                try:
                    avpreguntadocente = AvPreguntaDocente.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                    avpreguntadocente.delete()
                    log(u'Alumno elimino pregunta:%s' % avpreguntadocente, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'responder':
                try:
                    avpreguntadocente = AvPreguntaDocente.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                    avpreguntarespuesta = AvPreguntaRespuesta(avpreguntadocente=avpreguntadocente,
                                                              materiaasignada=avpreguntadocente.materiaasignada,
                                                              respuesta=request.POST['respuesta'])
                    avpreguntarespuesta.save(request)
                    avpreguntadocente.estadolectura = True
                    avpreguntadocente.save(request)
                    log(u'Alumno responde pregunta del docente:%s [%s] - respuesta: %s [%s]' % (avpreguntadocente,avpreguntadocente.id, avpreguntarespuesta, avpreguntarespuesta.id ), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'mostrarsilabodigital':
                try:
                    if 'idm' in request.POST:
                        silabo= Silabo.objects.get(materia_id=int(request.POST['idm']), status=True, profesor=int(request.POST['idp']))
                        return  conviert_html_to_pdf(
                            'pro_planificacion/silabo_pdf.html',
                            # 'alu_documentos/silabodigital_pdf.html',
                            {
                                'pagesize': 'A4',
                                'data': silabo.silabo_pdf(),
                            }
                        )
                except Exception as ex:
                    pass

            elif action == 'practica_indpdf':
                try:
                    practica = GPGuiaPracticaSemanal.objects.get(status=True, pk=int(request.POST['id']))
                    data['practicas'] = GPGuiaPracticaSemanal.objects.filter(status=True, id=practica.id)
                    data['decano'] = practica.silabosemanal.silabo.materia.coordinacion_materia().responsable_periododos(practica.silabosemanal.silabo.materia.nivel.periodo, 1) if practica.silabosemanal.silabo.materia.coordinacion_materia().responsable_periododos(practica.silabosemanal.silabo.materia.nivel.periodo, 1) else None
                    data['director'] = practica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.coordinador(practica.silabosemanal.silabo.materia.nivel.periodo, practica.silabosemanal.silabo.profesor.coordinacion.sede).persona.nombre_completo_inverso() if practica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.coordinador(practica.silabosemanal.silabo.materia.nivel.periodo, practica.silabosemanal.silabo.profesor.coordinacion.sede) else None
                    return conviert_html_to_pdf(
                        'pro_planificacion/practica_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'addcliczoom':
                try:
                    hoy = datetime.now().date()
                    horaactual= datetime.now().time()
                    horario=HorarioExamen.objects.get(id=int(encrypt_alu(request.POST['idhe'])))
                    # detalle=horario.horarioexamendetalle_set.filter(status=True)
                    # horainiciod=detalle[0].horainicio
                    # horafind=detalle.latest('id').horafin
                    #
                    # d2 = datetime(hoy.year, hoy.month, hoy.day, horainiciod.hour, horainiciod.minute)
                    # turnocomienza = (d2 - timedelta(minutes=15))
                    #
                    # if hoy==horario.fecha:
                    #     if horaactual >=turnocomienza.time() and horaactual<=horafind:
                    materiaasignada = MateriaAsignada.objects.get(id=int(encrypt_alu(request.POST['idma'])))
                    if not SesionZoom.objects.filter(materiaasignada=materiaasignada, status=True, fecha=horario.fecha, modulo=2).exists():
                        zoom = SesionZoom(
                            materiaasignada=materiaasignada,
                            modulo=2,
                            fecha=horario.fecha,
                            hora=datetime.now().time(),
                        )
                        zoom.save(request)
                    else:
                        zoom = SesionZoom.objects.filter(materiaasignada=materiaasignada, status=True, fecha=horario.fecha, modulo=2)[0]
                        zoom.horaultima = datetime.now().time()
                        zoom.save(request)

                    client_address = get_client_ip(request)
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    screensize = request.POST['screensize']
                    detalle = DetalleSesionZoom(
                        sesion=zoom,
                        ip_public=client_address,
                        browser=browser,
                        screen_size=screensize,
                        ops=ops,
                        fecha=datetime.now().date(),
                        hora=datetime.now().time()
                    )
                    detalle.save()

                    log(u'Alumno registra asistencia de acceso a examen:%s ' % (zoom), request,"add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'planificacion':
                try:
                    data['title'] = u'Planificacion de la materia'
                    materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    data['materia'] = materiaasignada.materia
                    data['materiaasignada'] = materiaasignada
                    data['modalidadcarrera'] = inscripcion.modalidad_id
                    data['comunicados'] = materiaasignada.materia.avcomunicacion_set.filter(visible=True).order_by("-fecha_creacion")[:4]
                    # data['planificaciones'] = materiaasignada.materia.planificacionmateria_set.filter(desde__lte=datetime.now().date())
                    return render(request, "alu_documentos/planificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'comunicacion':
                try:
                    data['title'] = u'Comunicación'
                    materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    data['materia'] = materiaasignada.materia
                    data['comunicados'] = materiaasignada.materia.avcomunicacion_set.filter(visible=True).order_by("-fecha_creacion")
                    return render(request, "alu_documentos/comunicacionmasiva.html", data)
                except Exception as ex:
                    pass

            elif action == 'deberes':
                try:
                    data['title'] = u'Deberes por clases'
                    materia = Materia.objects.get(pk=request.GET['id'])
                    lecciones = Leccion.objects.filter(clase__materia=materia).order_by('-fecha', '-horaentrada')
                    data['lecciones'] = lecciones
                    data['materia'] = materia
                    return render(request, "alu_documentos/deberes.html", data)
                except Exception as ex:
                    pass

            elif action == 'asistenciazoom':
                try:
                    data['title'] = u'Mi asistencia'
                    materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    asis = materiaasignada.asistencias_zoom()


                    # for fechas in materiaasignada.materia.lecciones_zoom():
                    #     if SesionZoom.objects.filter(materiaasignada=materiaasignada, fecha=fechas.fecha).exists():
                    #         asistencia = SesionZoom.objects.filter(materiaasignada=materiaasignada,
                    #                                                fecha=fechas.fecha)
                    #     else:
                    #         asistencia = False
                    #     asis.append(asistencia)


                    data['asistencia'] = asis
                    data['materia'] = materiaasignada
                    return render(request, "alu_documentos/asistencia_zoom.html", data)
                except Exception as ex:
                    pass

            elif action == 'controlacademico':
                try:
                    data['title'] = u'Orientación y Acompañamiento Académico'
                    data['materiaasignada'] = request.GET['id']
                    data['preguntas'] = AvPreguntaDocente.objects.filter(materiaasignada=int(encrypt_alu(request.GET['id'])), status=True)
                    data['modalidadcarrera'] = inscripcion.modalidad_id
                    return render(request, "alu_documentos/acompanamiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'conversacion':
                try:
                    data['title'] = u'Ingresar Pregunta'
                    form = AvPreguntaDocenteForm()
                    materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    form.combo(materiaasignada.materia)
                    data['materiaasignada'] = materiaasignada
                    data['form'] = form
                    return render(request, "alu_documentos/pregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconversacion':
                try:
                    data['title'] = u'Modificar Pregunta'
                    avpreguntadocente = AvPreguntaDocente.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    form = AvPreguntaDocenteForm(initial={'tema': avpreguntadocente.tema,
                                                          'profersormateria': avpreguntadocente.profersormateria,
                                                          'pregunta': avpreguntadocente.pregunta})
                    form.combo(avpreguntadocente.materiaasignada.materia)
                    form.editar()
                    data['avpreguntadocente'] = avpreguntadocente
                    data['form'] = form
                    return render(request, "alu_documentos/editpregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteconversacion':
                try:
                    data['title'] = u'Delete Pregunta'
                    data['avpreguntadocente'] = AvPreguntaDocente.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    return render(request, "alu_documentos/delpregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirdeberplanificacion':
                try:
                    data['title'] = u'Subir archivo de tarea de planificación'
                    data['miplanificacion'] = MateriaAsignadaPlanificacion.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    data['form'] = ArchivoPlanificacionForm()
                    return render(request, "alu_documentos/subirdeberplanificacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deldeberplanificacion':
                try:
                    data['title'] = u'Eliminar deber de planificación'
                    data['miplanificacion'] = MateriaAsignadaPlanificacion.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    return render(request, "alu_documentos/deldeberplanificacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'respuesta':
                try:
                    data['title'] = u'Orientación y Acompañamiento Académico'
                    data['preguntas'] = AvPreguntaRespuesta.objects.filter(avpreguntadocente__id=int(encrypt_alu(request.GET['id'])), status=True)
                    data['avpreguntadocente'] = avpreguntadocente = AvPreguntaDocente.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    avpreguntadocente.estadolecturaalumno = False
                    avpreguntadocente.save(request)
                    return render(request, "alu_documentos/respuestas.html", data)
                except Exception as ex:
                    pass

            elif action == 'silabo':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt_alu(request.GET['idm'])))
                    data['profesor'] = profesor = materia.profesor_principal()
                    data['silabos'] = materia.silabo_set.filter(profesor=profesor, status=True)
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    template = get_template("alu_documentos/listasilabos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'bibliografia':
                data['title'] = u'Bibliografía básica y complementaria'
                data['alumno'] = inscripcion
                data['materia'] = materia = Materia.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                bibliografiabasicas = []
                complementarias = []
                if materia.silabo_actual():
                    bibliografiabasicas = materia.silabo_actual().programaanaliticoasignatura.bibliografiaprogramaanaliticoasignatura_set.values_list('librokohaprogramaanaliticoasignatura_id', flat=False).filter(status=True).distinct()
                    complementarias = DetalleSilaboSemanalBibliografiaDocente.objects.values_list('librokohaprogramaanaliticoasignatura_id', flat=False).filter(status=True, silabosemanal__silabo=materia.silabo_actual()).distinct()
                librosinvestigacion = LibroKohaProgramaAnaliticoAsignatura.objects.filter(Q(status=True), (Q(pk__in=complementarias)| Q(pk__in=bibliografiabasicas))).distinct().order_by('nombre')
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    if len(ss) == 1:
                        librosinvestigacion = librosinvestigacion.filter(Q(nombre__icontains=search)| Q(autor__icontains=search)| Q(editorial__icontains=search), status=True)
                    else:
                        librosinvestigacion = librosinvestigacion.filter((Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1])) |  (Q(autor__icontains=ss[0]) &Q(autor__icontains=ss[1])) | (Q(editorial__icontains=ss[0]) &Q(editorial__icontains=ss[0])), Q(status=True))
                paging = MiPaginador(librosinvestigacion, 20)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['librosbiblioteca'] = page.object_list
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                return render(request, "alu_documentos/bibliografia.html", data)

            elif action == 'guiapracticas':
                try:
                    data['title'] = u'Guías de prácticas'
                    materia = Materia.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    practica = None
                    if materia.silabo_actual():
                        practica = GPGuiaPracticaSemanal.objects.filter(Q(status=True), Q(silabosemanal__silabo=materia.silabo_actual()), (Q(estadoguiapractica__estado=2)| Q(estadoguiapractica__estado=3)))
                    data['practicas'] = practica
                    data['materia'] = '%s - %s - %s %s' %(materia.asignaturamalla.asignatura, materia.asignaturamalla.nivelmalla, materia.paralelo, materia.nivel.paralelo)
                    return render(request, "alu_documentos/guiaspractica.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Aula Virtual'
                data['matricula'] = matricula = Matricula.objects.db_manager("sga_select").filter(inscripcion=inscripcion, nivel__periodo=periodo).first()
                if not matricula:
                    return HttpResponseRedirect("/?info=Ud. aun no ha sido matriculado")
                # if matricula.estado_matricula == 1:
                #
                #     return HttpResponseRedirect("/?info=Ud. aun no ha cancelado valores pendientes por matriculado")
                data['materiasasignadas'] = matricula.materiaasignada_set.db_manager("sga_select").filter(retiramateria=False)
                data['usa_planificacion'] = USA_PLANIFICACION
                data['inscripcionmalla'] = inscripcionmalla = InscripcionMalla.objects.db_manager("sga_select").get(inscripcion=inscripcion)
                contar_llenos=0
                if inscripcionmalla.malla.perfilegreso:
                    contar_llenos+=1
                if inscripcionmalla.malla.perfilprofesional:
                    contar_llenos += 1
                if inscripcionmalla.malla.objetivocarrera:
                    contar_llenos += 1
                if inscripcionmalla.malla.misioncarrera:
                    contar_llenos += 1
                data['contar_llenos'] = contar_llenos
                data['modalidadcarrera'] = inscripcion.modalidad_id
                data['OCULTAR_EXAMEN'] = variable_valor('OCULTAR_EXAMEN')
                return render(request, "alu_documentos/view.html", data)
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

