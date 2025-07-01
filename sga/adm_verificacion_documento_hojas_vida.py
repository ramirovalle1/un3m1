# -*- coding: UTF-8 -*-
import random

from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import json
from django.template import Context
from django.template.loader import get_template
from datetime import datetime, timedelta

from xlwt import easyxf, XFStyle, Workbook

from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from sagest.forms import DeportistaValidacionForm, DiscapacidadValidacionForm
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import SolicitudForm, TipoDiscapacidadForm, SubTipoDiscapacidadForm, PeriodoActulizacionForm
from django.db.models.aggregates import Avg
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import RecordAcademico, SolicitudMatricula, SolicitudDetalle, Matricula, MateriaAsignada, TipoSolicitud, \
    ConfiguracionTerceraMatricula, Inscripcion, DeportistaPersona, Carrera, DisciplinaDeportiva, PerfilInscripcion, \
    Coordinacion, NivelMalla, Discapacidad, SubTipoDiscapacidad, PeriodoActulizacionHojaVida, \
    InscripcionesPeriodoActulizacionHojaVida, Titulacion, NivelTitulacion
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'verificar':
            try:
                data['id'] = id = int(encrypt(request.POST['id']))
                periodoact = InscripcionesPeriodoActulizacionHojaVida.objects.get(id=id)
                periodoact.estado = int(request.POST['aprobar'])
                if int(request.POST['aprobar']) == 1:
                    periodoact.observacionrechazo = request.POST['observacionrechazo']
                periodoact.save(request)
                log(u'Aprobó/Rechazó hoja de vida: %s' % periodoact, request, "edit")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        # PERIODO DE ACTUALIZACION
        elif action == 'addperiodo':
            try:
                f = PeriodoActulizacionForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                        return JsonResponse({"result": True, "mensaje": u"La fecha fin debe ser mayor a la fecha inicio"})
                    if PeriodoActulizacionHojaVida.objects.filter(Q(status=True), Q(fechainicio__range=[f.cleaned_data['fechainicio'], f.cleaned_data['fechafin']]) | Q(fechafin__range=[f.cleaned_data['fechainicio'], f.cleaned_data['fechafin']])).exists():
                        return JsonResponse({"result": True, 'mensaje':'Ya existe un periodo en el rango de fechas ingresado'}, safe=False)
                    periodo = PeriodoActulizacionHojaVida(fechainicio=f.cleaned_data['fechainicio'],
                                                    fechafin=f.cleaned_data['fechafin'], observacion=f.cleaned_data['observacion'])
                    periodo.save(request)
                    log(u'Agrego periodo de Actualizacion de hoja de vida: %s' % periodo, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
        elif action == 'editperiodo':
            try:
                data['id'] = id = int(encrypt(request.POST['id']))
                periodoact = PeriodoActulizacionHojaVida.objects.get(id=id)
                f = PeriodoActulizacionForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                        return JsonResponse(
                            {"result": True, "mensaje": u"La fecha fin debe ser mayor a la fecha inicio"})
                    if PeriodoActulizacionHojaVida.objects.filter(Q(status=True), Q(fechainicio__range=[f.cleaned_data['fechainicio'], f.cleaned_data['fechafin']]) | Q(
                                                                          fechafin__range=[f.cleaned_data['fechainicio'], f.cleaned_data['fechafin']])).exclude(id=periodoact.pk).exists():
                        return JsonResponse({"result": True, 'mensaje': 'Ya existe un periodo en el rango de fechas ingresado'}, safe=False)
                    periodoact.fechainicio = f.cleaned_data['fechainicio']
                    periodoact.fechafin = f.cleaned_data['fechafin']
                    periodoact.observacion = f.cleaned_data['observacion']
                    periodoact.save(request)
                    log(u'Edito periodo de Actualizacion de hoja de vida: %s' % periodoact, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
        elif action == 'delperiodo':
            try:
                data['id'] = id = request.POST['id']
                periodoact = PeriodoActulizacionHojaVida.objects.get(id=id)
                periodoact.status = False
                periodoact.save(request)
                log(u'Elimino periodo de actualizacion: %s' % periodoact, request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al guardar los datos."})
        elif action == 'changestadoperiodo':
            try:
                data['id'] = id = request.POST['id']
                periodoact = PeriodoActulizacionHojaVida.objects.get(id=id)
                periodoact.estado = 1 if not periodoact.estado == 1 else 2
                periodoact.save(request)
                log(u'Cambio de estado el periodo de actualizacion: %s' % periodoact, request, "edit")
                return JsonResponse({"result": 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # INSCRIBIR POBLACION

        elif action == 'inscribirrevision':
            try:
                id = request.POST['id']
                per = int(encrypt(request.POST['periodoact']))
                if request.POST['todos'] == 'true':
                    for id in json.loads(id):
                        inscr = InscripcionesPeriodoActulizacionHojaVida(periodoactualizacion_id=per, inscripcion_id=id)
                        inscr.save(request)
                        log(u'Agrego periodo de Actualizacion de hoja de vida: %s' % periodo, request, "add")
                else:
                    inscr = InscripcionesPeriodoActulizacionHojaVida(periodoactualizacion_id=per, inscripcion_id=id)
                    inscr.save(request)
                    log(u'Agrego inscripcion para actualizacion de hoja de vida: %s' % inscr, request, "add")
                return JsonResponse({"result": False}, safe=False)
            except Exception as e:
                return JsonResponse({"result": True, 'mensaje': str(e)}, safe=False)
        elif action == 'delinscripcion':
            try:
                data['id'] = id = request.POST['id']
                insc = InscripcionesPeriodoActulizacionHojaVida.objects.get(id=id)
                if insc.estado == 2:
                    insc.delete()
                    return JsonResponse({"error": False})
                else:
                    return JsonResponse({"error": True, "mensaje": u"No puede eliminar esta inscripcion"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #  VOLVER A REVISAR

        if action == 'revivirrevision':
            try:
                data['id'] = id = request.POST['id']
                insc = InscripcionesPeriodoActulizacionHojaVida.objects.get(id=id)
                if insc.estado == 0:
                    insc.estado = 2
                    insc.save(request)
                    return JsonResponse({"error": False})
                else:
                    return JsonResponse({"error": True, "mensaje": u"No puede realizar esta acción"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'verificar':
                try:
                    data['title'] = u'Verificacion de Hoja de Vida'
                    data['alumno'] = alumno = InscripcionesPeriodoActulizacionHojaVida.objects.get(id=int(encrypt(request.GET['id'])))
                    data['periodoact'] = alumno.periodoactualizacion
                    data['persona'] = personaalumno = alumno.inscripcion.persona
                    data['perfilprincipal'] = perfilprincipal = personaalumno.perfil_inscripcion()
                    data['gastospersonales'] = personaalumno.gastospersonales_set.all().order_by('-periodogastospersonales__anio', '-mes')
                    data['datosextension'] = personaalumno.datos_extension()
                    data['documentopersonal'] = personaalumno.documentos_personales()
                    data['perfil'] = personaalumno.mi_perfil()
                    data['archivos'] = perfilprincipal.inscripcion.archivo_set.filter(status=True)
                    idtitulaciones = Titulacion.objects.filter(status=True, persona=personaalumno).values_list('titulo__nivel__id', flat=True)
                    data['niveltitulo'] = NivelTitulacion.objects.filter(status=True, id__in=idtitulaciones)

                    return render(request, "adm_verificacion_documento/hojas_vida/verificar.html", data)
                except Exception as ex:
                    pass

            # PERIODOS
            if action == 'addperiodo':
                form = PeriodoActulizacionForm()
                data['form'] = form
                data['action'] = action
                template = get_template("adm_verificacion_documento/hojas_vida/periodoform.html")
                return JsonResponse({"result": True, 'data': template.render(data)})
            if action == 'editperiodo':
                data['id'] = id = request.GET['id']
                periodoact = PeriodoActulizacionHojaVida.objects.get(id=id)
                form = PeriodoActulizacionForm(initial=model_to_dict(periodoact))
                data['form'] = form
                data['action'] = action
                template = get_template("adm_verificacion_documento/hojas_vida/periodoform.html")
                return JsonResponse({"result": True, 'data': template.render(data)})

            # POBLACION
            if action == 'poblacion':
                try:
                    periodoact = PeriodoActulizacionHojaVida.objects.get(id=int(encrypt(request.GET['id'])))
                    data['title'] = 'Población del periodo'
                    search = None
                    estadoselect = 3
                    problacionperiodo = periodoact.poblacion()
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            problacionperiodo = problacionperiodo.filter((Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                  Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                  Q(inscripcion__persona__nombres__icontains=search) |
                                                                                  Q(inscripcion__persona__cedula__icontains=search)))
                        else:
                            problacionperiodo = problacionperiodo.filter((Q(inscripcion__persona__nombres__icontains=ss[0]) & Q(inscripcion__persona__nombres__icontains=ss[1]) |
                                                                                  Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(inscripcion__persona__apellido2__icontains=ss[1])))
                    if 'est' in request.GET:
                        estado = int(request.GET['est'])
                        estadoselect = estado
                        if estado <= 2:
                            problacionperiodo = problacionperiodo.filter(estado=estado)
                    problacionperiodo = problacionperiodo.order_by("id")
                    data['total'] = len(problacionperiodo)

                    paging = MiPaginador(problacionperiodo, 25)

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
                    data['poblacion'] = page.object_list
                    data['periodoact'] = periodoact
                    data['estadoselect'] = estadoselect
                    data['caduca'] = (periodoact.fechafin - timedelta(days=1)) == datetime.now().date()
                    data['rango'] = len(page.object_list)
                    data['search'] = search if search else ""
                    return render(request, "adm_verificacion_documento/hojas_vida/view_poblacion.html", data)
                except Exception as ex:
                    data['msg_error'] = ex.__str__()
                    pass
            if action == 'addpoblacion':
                try:
                    search = ''
                    data['action'] = action
                    data['periodoact'] =  periodoact = PeriodoActulizacionHojaVida.objects.get(id=int(encrypt(request.GET['id'])))
                    data['coordinaciones'] = coordinaciones = Coordinacion.objects.filter(status=True, id__lte=5)
                    carreras = Carrera.objects.filter(status=True, coordinacion__in=coordinaciones.values_list('id', flat=True))
                    data['niveles'] = niveles = NivelMalla.objects.filter(status=True)
                    #perfilusuario__status=True, perfilusuario__visible=True, perfilusuario__inscripcionprincipal=True
                    filtro = Q(status=True, perfilusuario__status=True, perfilusuario__visible=True, perfilusuario__inscripcionprincipal=True)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro =  filtro & (Q(persona__nombres__icontains=search) | Q(persona__apellido1__icontains=search) |
                                                                 Q(persona__apellido2__icontains=search) |
                                                                 Q(persona__cedula__icontains=search) |
                                                                 Q(persona__pasaporte__icontains=search))
                        else:
                            filtro = filtro & (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))
                    carreraselect = 0
                    if 'c' in request.GET:
                        carreraselect = int(request.GET['c'])
                        data['c'] = carreraselect
                        if carreraselect > 0:
                            filtro = filtro & Q(carrera_id=carreraselect)

                    modalidadselect = 0
                    if 'm' in request.GET:
                        modalidadselect = int(request.GET['m'])
                        data['m'] = modalidadselect
                        if modalidadselect > 0:
                            filtro = filtro & Q(modalidad_id=modalidadselect)

                    facultadselect = 0
                    if 'f' in request.GET:
                        facultadselect = int(request.GET['f'])
                        data['f'] = facultadselect
                        if facultadselect > 0:
                            filtro = filtro & Q(coordinacion_id=facultadselect)
                            carreras = carreras.filter(coordinacion=facultadselect)
                    else:
                        filtro = filtro & Q(coordinacion_id__in=coordinaciones.values_list('id', flat=True))

                    excludes = InscripcionesPeriodoActulizacionHojaVida.objects.filter(status=True, periodoactualizacion=periodoact).values_list('inscripcion_id', flat=True)

                    inscripciones = Inscripcion.objects.filter(filtro).exclude(id__in=excludes).order_by('persona__apellido1').distinct()

                    nivelselect = 0
                    if 'nivel' in request.GET:
                        filtrosub = Q(status=True)
                        if facultadselect:
                            filtrosub = filtrosub & Q(inscripcion__carrera__coordinacion=facultadselect)
                        if carreraselect:
                            filtrosub = filtrosub & Q(inscripcion__carrera_id=carreraselect)
                        if modalidadselect:
                            filtrosub = filtrosub & Q(inscripcion__modalidad_id=modalidadselect)
                        nivelselect = int(request.GET['nivel']) if not request.GET['nivel'] == 'undefined' else 0
                        data['nivel'] = nivelselect
                        if nivelselect > 0:
                            inscripciones_nivel = Matricula.objects.filter(nivelmalla_id=nivelselect,
                                                                           nivel__periodo=periodo).filter(
                                filtrosub).values_list('inscripcion_id', flat=True)
                            inscripciones = inscripciones.filter(id__in=inscripciones_nivel).order_by(
                                'persona__apellido1').distinct()
                    else:
                        inscripciones = inscripciones.distinct()


                    data['total'] = total = len(inscripciones)
                    counter_page = 100 if total <= 500 else 25
                    paging = MiPaginador(inscripciones, counter_page)
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
                    data['inscripciones'] = page.object_list
                    data['carreras'] = carreras
                    data['rango'] = len(page.object_list)
                    data['search'] = search if search else ""
                    data['carreraselect'] = carreraselect
                    data['facultadselect'] = facultadselect
                    data['modalidadselect'] = modalidadselect
                    data['nivelselect'] = nivelselect
                    data['insc_todos'] = list(inscripciones.values_list('id', flat=True))
                    return render(request, "adm_verificacion_documento/hojas_vida/addpoblacion.html", data)
                except Exception as ex:
                    data['msg_error'] = ex.__str__()
                pass


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Periodos de actualización de hojas de vida'
                search = None
                ids = None
                inscripcionid = None
                # cursor = connection.cursor()
                periodosact = PeriodoActulizacionHojaVida.objects.filter(status=True)
                if 's' in request.GET:
                    search = request.GET['s']
                    data['s'] = search
                    periodosact = periodosact.filter(descripcion__icontains=search)
                periodosact = periodosact.order_by("id")
                data['total'] = len(periodosact)

                paging = MiPaginador(periodosact, 25)


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
                data['periodosact'] = page.object_list
                data['rango'] = len(page.object_list)
                data['search'] = search if search else ""
                return render(request, "adm_verificacion_documento/hojas_vida/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                pass #return render(request, "alu_solicitudmatricula/error.html", data)
