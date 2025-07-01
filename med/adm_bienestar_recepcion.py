import random
from datetime import datetime, date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models.query_utils import Q
from django.db import transaction
from decorators import secure_module, last_access
from med.forms import RegistrarIngresoBienestarForm
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sagest.models import DistributivoPersona
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha
from sga.models import Inscripcion, Matricula, Periodo, Carrera
from med.models import RegistrarIngresoBienestar
from django.template.context import Context
from django.template.loader import get_template


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addadministrativo':
            try:
                if 'id' in request.POST:
                    administrativo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                    reg = RegistrarIngresoBienestar(persona=administrativo.persona,
                                                  regimenlaboral=administrativo.regimenlaboral,
                                                  fecha=datetime.now().date(),
                                                  horainicio=datetime.now().time())
                    reg.save(request)
                    log(u'Adicionó una nueva visita de administrativo: %s' % reg.persona, request,"add")
                    return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'registrarvisita':
            try:
                if 'id' in request.POST:
                    reg = RegistrarIngresoBienestar(actividad=request.POST['observacion'],
                                                    fecha=datetime.now().date(),
                                                    tiposerviciobienestar_id=int(request.POST['tiposerviciobienestar']),
                                                    horainicio=datetime.now().time()
                                                    )
                    if int(request.POST['tipo']) == 1:
                        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                        reg.inscripcion = inscripcion
                    elif int(request.POST['tipo']) == 2:
                        administrativo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                        reg.persona = administrativo.persona
                        reg.regimenlaboral = administrativo.regimenlaboral
                    reg.save(request)
                    log(u'Adicionó una nueva visita de incripcion: %s' % reg, request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delvisita':
            try:
                visita = RegistrarIngresoBienestar.objects.get(pk=int(request.POST['id']))
                log(u'Elimino la visita de: %s' % visita.persona if visita.persona else visita.inscripcion.persona, request, "add")
                visita.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'reportegeneral_pdf':
            try:
                if 'de' in request.POST and 'hasta' in request.POST:
                    data['fecha'] = datetime.now().date()
                    data['fechade'] = convertir_fecha(request.POST['de'])
                    data['fechahasta'] = convertir_fecha(request.POST['hasta'])
                    data['cantidad_estudiantes'] = cant_est =  RegistrarIngresoBienestar.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True).count()
                    data['cantidad_administrativo'] =cant_adm =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True).count()
                    data['cantidad_docententes'] = cant_doc =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True).count()
                    data['cantidad_trabajadores'] = cant_tra =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True).count()
                    data['total'] = cant_est + cant_adm + cant_doc + cant_tra
                    return conviert_html_to_pdf(
                        'box_recepcion/reportegeneral_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
            except Exception as ex:
                pass

        elif action == 'reporte_pdf':
            try:
                if 'de' in request.POST and 'hasta' in request.POST:
                    data['fechade'] = convertir_fecha(request.POST['de'])
                    data['fechahasta'] = convertir_fecha(request.POST['hasta'])
                    if 'tipo' in request.POST and int(request.POST['tipo'])>0:
                        if int(request.POST['tipo']) == 1:
                            data['administrativos'] = administradores = RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        elif int(request.POST['tipo']) == 2:
                            data['trabajadores'] = trabajadores = RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        elif int(request.POST['tipo']) == 3:
                            data['docentes'] = docentes = RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])),status=True)
                        else:
                            data['estudiantes'] = estudiantes = RegistrarIngresoBienestar.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])),status=True)
                    else:
                        data['fecha'] = datetime.now().date()
                        data['estudiantes'] = estudiantes =  RegistrarIngresoBienestar.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True)
                        data['administrativos'] = administradores =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True)
                        data['docentes'] = docentes =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        data['trabajadores'] = trabajadores =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)

                else:
                    if 'tipo' in request.POST and int(request.POST['tipo'])>0:
                        if int(request.POST['tipo']) == 1:
                            data['administrativos'] = administradores = RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, status=True)
                        elif int(request.POST['tipo']) == 2:
                            data['trabajadores'] = trabajadores = RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, status=True)
                        elif int(request.POST['tipo']) == 3:
                            data['docentes'] = docentes = RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, status=True)
                        else:
                            data['estudiantes'] = estudiantes = RegistrarIngresoBienestar.objects.filter(persona__isnull=True, status=True)
                    else:
                        data['estudiantes'] = estudiantes =  RegistrarIngresoBienestar.objects.filter(persona__isnull=True, status= True)
                        data['administrativos'] = administradores =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, status= True)
                        data['docentes'] = docentes =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, status=True)
                        data['trabajadores'] = trabajadores =  RegistrarIngresoBienestar.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, status=True)
                data['tipo'] = int(request.POST['tipo'])
                data['fecha'] = datetime.now().date()
                return conviert_html_to_pdf(
                    'box_recepcion/reporte_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'reqistrar_salida':
            try:
                if 'id' in request.POST:
                    visita = RegistrarIngresoBienestar.objects.get(pk=int(request.POST['id']))
                    visita.horafin = datetime.now().time()
                    visita.save(request)
                    log(u'Registro hora de salida a la visita de la persona: %s' % visita.persona if visita.persona else visita.inscripcion.persona, request, "add")
                    return JsonResponse({"result": "ok", "horafin": visita.horafin.strftime("%H:%M ")})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al registrar hora salida."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'reqistrar_observacion':
            try:
                if 'id' in request.POST and 'observacion' in request.POST:
                    visita = RegistrarIngresoBienestar.objects.get(pk=int(request.POST['id']))
                    visita.actividad = request.POST['observacion']
                    visita.save(request)
                    log(u'Registro observacion a la visita de la persona: %s' % visita.persona if visita.persona else visita.inscripcion.persona, request, "add")
                    return JsonResponse({"result": "ok", "observacion": visita.actividad})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al registrar la observación."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'observacion':
            try:
                if 'id' in request.POST:
                    visita = RegistrarIngresoBienestar.objects.get(pk=int(request.POST['id']))
                    return JsonResponse({"result": "ok", "observacion": visita.actividad, "tiene_horafin": True if visita.horafin else False })
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al registrar la observación."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'delvisita':
                try:
                    data['title'] = u'Eliminar la Práctica'
                    data['visita'] =  RegistrarIngresoBienestar.objects.get(pk=int(request.GET['id']))
                    return render(request, "box_recepcion/delvisita.html", data)
                except Exception as ex:
                    pass

            elif action == 'administrativos':
                try:
                    data['title'] = u'Listado de personal administrativo'
                    search = None
                    ids = None
                    unemiper = RegistrarIngresoBienestar.objects.filter(status=True, persona__isnull=False, fecha=datetime.now().date(), horafin__isnull=True)
                    listadist = []
                    for gym in unemiper:
                        listadist.append(DistributivoPersona.objects.filter(status= True, persona=gym.persona, regimenlaboral=gym.regimenlaboral, estadopuesto__id=PUESTO_ACTIVO_ID)[0].id)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            administrativos = DistributivoPersona.objects.filter(Q(estadopuesto__id=PUESTO_ACTIVO_ID) &
                                                                                 (Q(persona__nombres__icontains=search) |
                                                                                  Q(persona__apellido1__icontains=search) |
                                                                                  Q(persona__apellido2__icontains=search) |
                                                                                  Q(persona__cedula__icontains=search) |
                                                                                  Q(persona__pasaporte__icontains=search) |
                                                                                  Q(denominacionpuesto__descripcion__icontains=search))).exclude(id__in=listadist)
                        else:
                            administrativos = DistributivoPersona.objects.filter(Q(estadopuesto__id=PUESTO_ACTIVO_ID) &
                                                                                 (Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1]) |
                                                                                  Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]) |
                                                                                  Q(denominacionpuesto__descripcion__icontains=ss[0]) & Q(denominacionpuesto__descripcion__icontains=ss[1]))).exclude(id__in=listadist)
                    elif 'id' in request.GET:
                        administrativos = DistributivoPersona.objects.filter(Q(pk=int(request.GET['id'])) & Q(estadopuesto__id=PUESTO_ACTIVO_ID))
                    else:
                        administrativos = DistributivoPersona.objects.filter(estadopuesto__id=PUESTO_ACTIVO_ID).exclude(id__in=listadist)
                    paging = MiPaginador(administrativos, 15)
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
                    data['administrativos'] = page.object_list
                    return render(request, "box_recepcion/view_administrativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscripcion':
                data['title'] = u'Listado de estudiantes matriculados'
                try:
                    search = None
                    ids = None
                    carreraselect = 0
                    # periodos = Periodo.objects.values_list("id", flat=False).filter(inicio__lt=datetime.now().date(), fin__gt=datetime.now().date())
                    periodos = Periodo.objects.values_list("id", flat=False).filter(activo=True)
                    inscripciones = Inscripcion.objects.filter(pk__in=Matricula.objects.values_list("inscripcion", flat=False).filter(nivel__periodo__in=periodos)).exclude(registrarvisitagymumeni__fecha=datetime.now().date(), registrarvisitagymumeni__horafin__isnull=True)
                    carreras = Carrera.objects.filter(id__in=inscripciones.values_list("carrera_id", flat=False).all()).distinct()
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if 'c' in request.GET and int(request.GET['c']) > 0:
                            carreraselect = int(request.GET['c'])
                            if len(ss) == 1:
                                inscripciones = inscripciones.filter((Q(persona__nombres__icontains=search) |
                                                                      Q(persona__apellido1__icontains=search) |
                                                                      Q(persona__apellido2__icontains=search) |
                                                                      Q(persona__cedula__icontains=search) |
                                                                      Q(persona__pasaporte__icontains=search) |
                                                                      Q(identificador__icontains=search) |
                                                                      Q(inscripciongrupo__grupo__nombre__icontains=search) |
                                                                      Q(persona__usuario__username__icontains=search)) & Q(carrera_id=carreraselect)).exclude(registrarvisitagymumeni__fecha=datetime.now().date(), registrarvisitagymumeni__horafin__isnull=True)
                            else:
                                inscripciones = inscripciones.filter(((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1])) |
                                                                      (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))) & Q(carrera_id=carreraselect)).exclude(registrarvisitagymumeni__fecha=datetime.now().date(), registrarvisitagymumeni__horafin__isnull=True)
                        else:
                            if len(ss) == 1:
                                inscripciones = inscripciones.filter(Q(persona__nombres__icontains=search) |
                                                                     Q(persona__apellido1__icontains=search) |
                                                                     Q(persona__apellido2__icontains=search) |
                                                                     Q(persona__cedula__icontains=search) |
                                                                     Q(persona__pasaporte__icontains=search) |
                                                                     Q(identificador__icontains=search) |
                                                                     Q(inscripciongrupo__grupo__nombre__icontains=search) |
                                                                     Q(persona__usuario__username__icontains=search)).exclude(registrarvisitagymumeni__fecha=datetime.now().date(), registrarvisitagymumeni__horafin__isnull=True)
                            else:
                                inscripciones = inscripciones.filter((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1])) | (
                                    Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))).exclude(registrarvisitagymumeni__fecha=datetime.now().date(), registrarvisitagymumeni__horafin__isnull=True)
                    elif 'c' in request.GET:
                        if not int(request.GET['c']) == 0:
                            carreraselect = int(request.GET['c'])
                            if 'id' in request.GET:
                                inscripciones = inscripciones.filter(carrera_id=int(request.GET['c']), pk=int(request.GET['id']))
                            else:
                                inscripciones = inscripciones.filter(carrera_id=int(request.GET['c'])).exclude(registrarvisitagymumeni__fecha=datetime.now().date(), registrarvisitagymumeni__horafin__isnull=True)
                    paging = MiPaginador(inscripciones, 15)
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
                    data['carreraselect'] = carreraselect
                    data['carreras'] = carreras
                    return render(request, "box_recepcion/view_inscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrar':
                try:
                    data['title'] = u'Informe'
                    data['form'] = RegistrarIngresoBienestarForm
                    data['id'] = request.GET['id']
                    data['tipo'] = int(request.GET['tipo'])
                    if data['tipo'] == 1:
                        data['informacion'] = Inscripcion.objects.get(pk=int(request.GET['id'])).info()
                    elif data['tipo'] == 2:
                        data['informacion'] = DistributivoPersona.objects.get(pk=int(request.GET['id'])).info()
                    template = get_template("box_recepcion/registrar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Recepción de Visitas - Bienestar Universitario'
            try:
                search=None
                ids =None
                fecha = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if 'fecha' in request.GET:
                        fecha = convertir_fecha(request.GET['fecha'])
                        if len(ss) == 1:
                            visitas = RegistrarIngresoBienestar.objects.filter(Q(status=True), ((Q(persona__nombres__icontains=search) |
                                                                                               Q(persona__apellido1__icontains=search) |
                                                                                               Q(persona__apellido2__icontains=search) |
                                                                                               Q(persona__cedula__icontains=search))|(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__cedula__icontains=search))), Q(fecha=convertir_fecha(request.GET['fecha'])))
                        else:
                            visitas = RegistrarIngresoBienestar.objects.filter(Q(status=True),
                                                                             (((Q(persona__nombres__icontains=ss[0])& Q(persona__nombres__icontains=ss[0])) |
                                                                               (Q(persona__apellido1__icontains=ss[0]) &Q(persona__apellido2__icontains=ss[1]))) | (
                                                                                  (Q(inscripcion__persona__nombres__icontains=ss[0])& Q(inscripcion__persona__nombres__icontains=ss[1]))|
                                                                                  (Q(inscripcion__persona__apellido1__icontains=ss[0]) &Q(inscripcion__persona__apellido2__icontains=ss[1]))
                                                                              )), Q(fecha=convertir_fecha(request.GET['fecha'])))
                    else:
                        if len(ss) == 1:
                            visitas = RegistrarIngresoBienestar.objects.filter(Q(status=True), ((Q(persona__nombres__icontains=search) |
                                                                                               Q(persona__apellido1__icontains=search) |
                                                                                               Q(persona__apellido2__icontains=search) |
                                                                                               Q(persona__cedula__icontains=search))|(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__cedula__icontains=search))))
                        else:
                            visitas = RegistrarIngresoBienestar.objects.filter(Q(status=True),
                                                                             (((Q(persona__nombres__icontains=ss[0])& Q(persona__nombres__icontains=ss[0])) |
                                                                               (Q(persona__apellido1__icontains=ss[0]) &Q(persona__apellido2__icontains=ss[1]))) | (
                                                                                  (Q(inscripcion__persona__nombres__icontains=ss[0])& Q(inscripcion__persona__nombres__icontains=ss[1]))|
                                                                                  (Q(inscripcion__persona__apellido1__icontains=ss[0]) &Q(inscripcion__persona__apellido2__icontains=ss[1]))
                                                                              )))
                elif 'fecha' in request.GET:
                    visitas = RegistrarIngresoBienestar.objects.filter(status=True, fecha=convertir_fecha(request.GET['fecha'])).order_by('-horainicio')
                    fecha = convertir_fecha(request.GET['fecha'])
                else:
                    visitas = RegistrarIngresoBienestar.objects.filter(status=True, fecha=datetime.now().date()).order_by('-fecha','-horainicio')
                paging = MiPaginador(visitas, 10)
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
                data['visitas'] = page.object_list
                data['fechaselect'] = fecha
                data['hora'] = datetime.now().time().strftime("%H:%M")
                return render(request, "box_recepcion/view.html", data)
            except Exception as ex:
                pass


