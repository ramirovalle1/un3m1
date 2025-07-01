from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from sagest.models import DistributivoPersona
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import UtensiliosForm
from sga.funciones import MiPaginador, log, convertir_fecha
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Inscripcion, Matricula, Periodo, Carrera, RegistrarPolideportivo


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
                f = UtensiliosForm(request.POST)
                if f.is_valid():
                    if 'idadministrativo' in request.POST:
                        administrativo = DistributivoPersona.objects.get(pk=int(request.POST['idadministrativo']))
                        if RegistrarPolideportivo.objects.values('id').filter(status=True, persona=administrativo.persona, fecha=datetime.now().date(), horafin__isnull=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": administrativo.persona.nombre_completo_inverso() + ', ya se encuentra registrado el dia de hoy...'})
                        else:
                            reg = RegistrarPolideportivo(persona=administrativo.persona,
                                                          regimenlaboral=administrativo.regimenlaboral,
                                                          fecha=datetime.now().date(),
                                                          horainicio=datetime.now().time(),
                                                          utensilios=f.cleaned_data['utensilios'],
                                                          cantidad=f.cleaned_data['cantidad']
                                                         )
                            reg.save(request)
                            log(u'Adicionó una nueva visita polideportivo de administrativo: %s' % reg.persona, request,"add")
                            return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'existe_administrativo_activo':
                try:
                    if 'id' in request.POST:
                        distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                        if RegistrarPolideportivo.objects.values('id').filter(status=True, persona=distributivo.persona, fecha=datetime.now().date(), horafin__isnull=True).exists():
                            return JsonResponse({"result": "ok", "existe": True, "mensaje": distributivo.persona.nombre_completo_inverso() + ', ya se encuentra registrado el dia de hoy...'})
                        else:
                            return JsonResponse({"result": "ok", "existe": False})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addinscripcion':
            try:
                f = UtensiliosForm(request.POST)
                if f.is_valid():
                    if 'idinscripcion' in request.POST:
                        inscripcion = Inscripcion.objects.get(pk=int(request.POST['idinscripcion']))
                        if RegistrarPolideportivo.objects.values('id').filter(status=True, inscripcion=inscripcion, fecha=datetime.now().date(), horafin__isnull=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": inscripcion.persona.nombre_completo_inverso() + ', ya se encuentra registrado el dia de hoy...'})
                        else:
                            reg = RegistrarPolideportivo(inscripcion=inscripcion,
                                                          fecha=datetime.now().date(),
                                                          horainicio=datetime.now().time(),
                                                          utensilios=f.cleaned_data['utensilios'],
                                                          cantidad=f.cleaned_data['cantidad'])
                            reg.save(request)
                            log(u'Adicionó una nueva visita polideportivo de incripcion: %s' % reg.inscripcion.persona, request, "add")
                            return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delvisita':
            try:
                visita = RegistrarPolideportivo.objects.get(pk=int(request.POST['id']))
                log(u'Elimino la visita polideportivo de: %s' % visita.persona if visita.persona else visita.inscripcion.persona, request, "add")
                visita.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'reportegeneral_pdf':
            try:
                if 'de' in request.POST and 'hasta' in request.POST:
                    data['fecha'] = datetime.now().date()
                    data['fechade'] = convertir_fecha(request.POST['de'])
                    data['fechahasta'] = convertir_fecha(request.POST['hasta'])
                    data['cantidad_estudiantes'] = cant_est =  RegistrarPolideportivo.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True).count()
                    data['cantidad_administrativo'] =cant_adm =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True).count()
                    data['cantidad_docententes'] = cant_doc =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True).count()
                    data['cantidad_trabajadores'] = cant_tra =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=4, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True).count()
                    data['total'] = cant_est + cant_adm + cant_doc + cant_tra
                    return conviert_html_to_pdf(
                        'adm_polideportivo/reportegeneral_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
            except Exception as ex:
                pass

        if action == 'reporte_pdf':
            try:
                if 'de' in request.POST and 'hasta' in request.POST:
                    data['fechade'] = convertir_fecha(request.POST['de'])
                    data['fechahasta'] = convertir_fecha(request.POST['hasta'])
                    if 'tipo' in request.POST and int(request.POST['tipo'])>0:
                        if int(request.POST['tipo']) == 1:
                            data['administrativos'] = administradores = RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        elif int(request.POST['tipo']) == 2:
                            data['trabajadores'] = trabajadores = RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=4, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        elif int(request.POST['tipo']) == 3:
                            data['docentes'] = docentes = RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])),status=True)
                        else:
                            data['estudiantes'] = estudiantes = RegistrarPolideportivo.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])),status=True)
                    else:
                        data['fecha'] = datetime.now().date()
                        data['estudiantes'] = estudiantes =  RegistrarPolideportivo.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True)
                        data['administrativos'] = administradores =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True)
                        data['docentes'] = docentes =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        data['trabajadores'] = trabajadores =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=4, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)

                else:
                    if 'tipo' in request.POST and int(request.POST['tipo'])>0:
                        if int(request.POST['tipo']) == 1:
                            data['administrativos'] = administradores = RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, status=True)
                        elif int(request.POST['tipo']) == 2:
                            data['trabajadores'] = trabajadores = RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=4, status=True)
                        elif int(request.POST['tipo']) == 3:
                            data['docentes'] = docentes = RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, status=True)
                        else:
                            data['estudiantes'] = estudiantes = RegistrarPolideportivo.objects.filter(persona__isnull=True, status=True)
                    else:
                        data['estudiantes'] = estudiantes =  RegistrarPolideportivo.objects.filter(persona__isnull=True, status= True)
                        data['administrativos'] = administradores =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, status= True)
                        data['docentes'] = docentes =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, status=True)
                        data['trabajadores'] = trabajadores =  RegistrarPolideportivo.objects.filter(inscripcion__isnull=True, regimenlaboral__id=4, status=True)
                data['tipo'] = int(request.POST['tipo'])
                data['fecha'] = datetime.now().date()
                return conviert_html_to_pdf(
                    'adm_polideportivo/reporte_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'reqistrar_salida':
            try:
                if 'id' in request.POST:
                    visita = RegistrarPolideportivo.objects.get(pk=int(request.POST['id']))
                    visita.horafin = datetime.now().time()
                    visita.save(request)
                    log(u'Registro hora de salida a la visita polideportivo de la persona: %s' % visita.persona if visita.persona else visita.inscripcion.persona, request, "add")
                    return JsonResponse({"result": "ok", "horafin": visita.horafin.strftime("%H:%M ")})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al registrar hora salida."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'reqistrar_observacion':
            try:
                if 'id' in request.POST and 'observacion' in request.POST:
                    visita = RegistrarPolideportivo.objects.get(pk=int(request.POST['id']))
                    visita.observacion = request.POST['observacion']
                    tiene_horafin = False
                    if not visita.horafin:
                        visita.horafin = request.POST['horafin']
                        tiene_horafin = True
                    visita.save(request)
                    log(u'Registro observacion a la visita polideportivo de la persona: %s' % visita.persona if visita.persona else visita.inscripcion.persona, request, "add")
                    return JsonResponse({"result": "ok", "observacion": visita.observacion, "horafin": str(visita.horafin), "tiene_horafin": tiene_horafin })
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al registrar la observación."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'observacion':
            try:
                if 'id' in request.POST:
                    visita = RegistrarPolideportivo.objects.get(pk=int(request.POST['id']))
                    return JsonResponse({"result": "ok", "observacion": visita.observacion, "tiene_horafin": True if visita.horafin else False })
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al registrar la observación."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'existe_inscripcion_activa':
            try:
                if 'id' in request.GET:
                    inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    if RegistrarPolideportivo.objects.values('id').filter(status=True, inscripcion=inscripcion, fecha=datetime.now().date(), horafin__isnull=True).exists():
                        return JsonResponse({"result": "ok", "existe": True, "mensaje": inscripcion.persona.nombre_completo_inverso() + ', ya se encuentra registrado el dia de hoy...'})
                    else:
                        return JsonResponse({"result": "ok", "existe": False})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addadministrativo':
                try:
                    data['title'] = u'Registro utensilios POLIDEPORTIVO'
                    data['distributivopersona'] =  DistributivoPersona.objects.get(pk=int(request.GET['id']))
                    data['form'] = UtensiliosForm()
                    return render(request, "adm_polideportivo/addadministrativo.html", data)
                except Exception as ex:
                    pass

            if action == 'addinscripcion':
                try:
                    data['inscripcion'] = inscripcion =  Inscripcion.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Registro utensilios POLIDEPORTIVO ' + inscripcion.persona.nombre_completo_simple()
                    data['form'] = UtensiliosForm()
                    return render(request, "adm_polideportivo/addinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'delvisita':
                try:
                    data['title'] = u'Eliminar el Registro'
                    data['visita'] =  RegistrarPolideportivo.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_polideportivo/delvisita.html", data)
                except Exception as ex:
                    pass

            elif action == 'administrativos':
                try:
                    data['title'] = u'Listado de personal administrativo'
                    search = None
                    ids = None
                    unemiper = RegistrarPolideportivo.objects.filter(status=True, persona__isnull=False, fecha=datetime.now().date(), horafin__isnull=True)
                    listadist = []
                    for gym in unemiper:
                        listadist.append(DistributivoPersona.objects.filter(status= True, persona=gym.persona, regimenlaboral=gym.regimenlaboral, estadopuesto__id=PUESTO_ACTIVO_ID)[0].id)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            administrativos = DistributivoPersona.objects.filter(Q(estadopuesto__id=PUESTO_ACTIVO_ID) & (Q(regimenlaboral__id=1) | Q(regimenlaboral__id=2) | Q(regimenlaboral__id=4)) &
                                                                                 (Q(persona__nombres__icontains=search) |
                                                                                  Q(persona__apellido1__icontains=search) |
                                                                                  Q(persona__apellido2__icontains=search) |
                                                                                  Q(persona__cedula__icontains=search) |
                                                                                  Q(persona__pasaporte__icontains=search) |
                                                                                  Q(denominacionpuesto__descripcion__icontains=search))).exclude(id__in=listadist)
                        else:
                            administrativos = DistributivoPersona.objects.filter(Q(estadopuesto__id=PUESTO_ACTIVO_ID) & (Q(regimenlaboral__id=1) | Q(regimenlaboral__id=2) | Q(regimenlaboral__id=4)) &
                                                                                 (Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1]) |
                                                                                  Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]) |
                                                                                  Q(denominacionpuesto__descripcion__icontains=ss[0]) & Q(denominacionpuesto__descripcion__icontains=ss[1]))).exclude(id__in=listadist)
                    elif 'id' in request.GET:
                        administrativos = DistributivoPersona.objects.filter(Q(pk=int(request.GET['id']))& Q(estadopuesto__id=PUESTO_ACTIVO_ID) & (Q(regimenlaboral__id=1) | Q(regimenlaboral__id=2)|Q(regimenlaboral__id=4)))
                    else:
                        administrativos = DistributivoPersona.objects.filter(Q(estadopuesto__id=PUESTO_ACTIVO_ID) & (Q(regimenlaboral__id=1)|Q(regimenlaboral__id=2)|Q(regimenlaboral__id=4))).exclude(id__in=listadist)
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
                    return render(request, "adm_polideportivo/view_administrativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscripcion':
                data['title'] = u'Listado de estudiantes matriculados'
                try:
                    search = None
                    ids = None
                    carreraselect = 0
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
                    return render(request, "adm_polideportivo/view_inscripcion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Control de acceso al POLIDEPORTIVO'
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
                            visitas = RegistrarPolideportivo.objects.filter(Q(status=True), ((Q(persona__nombres__icontains=search) |
                                                                                               Q(persona__apellido1__icontains=search) |
                                                                                               Q(persona__apellido2__icontains=search) |
                                                                                               Q(persona__cedula__icontains=search))|(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__cedula__icontains=search))), Q(fecha=convertir_fecha(request.GET['fecha'])))
                        else:
                            visitas = RegistrarPolideportivo.objects.filter(Q(status=True),
                                                                             (((Q(persona__nombres__icontains=ss[0])& Q(persona__nombres__icontains=ss[0])) |
                                                                               (Q(persona__apellido1__icontains=ss[0]) &Q(persona__apellido2__icontains=ss[1]))) | (
                                                                                  (Q(inscripcion__persona__nombres__icontains=ss[0])& Q(inscripcion__persona__nombres__icontains=ss[1]))|
                                                                                  (Q(inscripcion__persona__apellido1__icontains=ss[0]) &Q(inscripcion__persona__apellido2__icontains=ss[1]))
                                                                              )), Q(fecha=convertir_fecha(request.GET['fecha'])))
                    else:
                        if len(ss) == 1:
                            visitas = RegistrarPolideportivo.objects.filter(Q(status=True), ((Q(persona__nombres__icontains=search) |
                                                                                               Q(persona__apellido1__icontains=search) |
                                                                                               Q(persona__apellido2__icontains=search) |
                                                                                               Q(persona__cedula__icontains=search))|(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__cedula__icontains=search))))
                        else:
                            visitas = RegistrarPolideportivo.objects.filter(Q(status=True),
                                                                             (((Q(persona__nombres__icontains=ss[0])& Q(persona__nombres__icontains=ss[0])) |
                                                                               (Q(persona__apellido1__icontains=ss[0]) &Q(persona__apellido2__icontains=ss[1]))) | (
                                                                                  (Q(inscripcion__persona__nombres__icontains=ss[0])& Q(inscripcion__persona__nombres__icontains=ss[1]))|
                                                                                  (Q(inscripcion__persona__apellido1__icontains=ss[0]) &Q(inscripcion__persona__apellido2__icontains=ss[1]))
                                                                              )))
                elif 'fecha' in request.GET:
                    visitas = RegistrarPolideportivo.objects.filter(status=True, fecha=convertir_fecha(request.GET['fecha'])).order_by('-horainicio')
                    fecha = convertir_fecha(request.GET['fecha'])
                else:
                    visitas = RegistrarPolideportivo.objects.filter(status=True).order_by('-fecha','-horainicio')
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
                data['reporte_1'] = obtener_reporte('prestamo_polideportivo')
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['visitas'] = page.object_list
                data['fechaselect'] = fecha
                data['hora'] = datetime.now().time().strftime("%H:%M")
                return render(request, "adm_polideportivo/view.html", data)
            except Exception as ex:
                pass


