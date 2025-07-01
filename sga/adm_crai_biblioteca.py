from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from sagest.forms import ClienteExternoCraiForm
from sga.commonviews import adduserdata
from sga.forms import RegistrarIngresoCraiForm, RegistrarPrestamoLibroForm
from sga.funciones import MiPaginador, log, convertir_fecha
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Inscripcion, RegistrarVisitaGymUmeni, RegistrarPrestamoLibro, Externo, \
    Persona, Periodo, Matricula


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
        if action == 'addinscripcion':
            try:
                if 'id' in request.POST:
                    form = RegistrarPrestamoLibroForm(request.POST)
                    if form.is_valid():
                        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                        matricula = None
                        if int(request.POST['idm']) > 0:
                            matricula = Matricula.objects.get(pk=int(request.POST['idm']))
                        reg = RegistrarPrestamoLibro(inscripcion=inscripcion,
                                                     matricula=matricula,
                                                     librokohaprogramaanaliticoasignatura_id=form.cleaned_data['librokohaprogramaanaliticoasignatura'],
                                                     tipoprestamo=form.cleaned_data['tipoprestamo'],
                                                     fecha=datetime.now().date(),
                                                     horainicio=datetime.now().today())
                        reg.save(request)
                        log(u'Adicionó una nueva registro libro incripcion crai: %s' % reg.inscripcion.persona, request, "add")
                        return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addinscripcionexterno':
            try:
                if 'id' in request.POST:
                    form = RegistrarPrestamoLibroForm(request.POST)
                    if form.is_valid():
                        persona = Persona.objects.get(pk=int(request.POST['id']))
                        reg = RegistrarPrestamoLibro(persona=persona,
                                                     librokohaprogramaanaliticoasignatura_id=form.cleaned_data['librokohaprogramaanaliticoasignatura'],
                                                     tipoprestamo=form.cleaned_data['tipoprestamo'],
                                                     fecha=datetime.now().date(),
                                                     horainicio=datetime.now().today())
                        reg.save(request)
                        log(u'Adicionó una nueva registro libro incripcion externo crai: %s' % reg.persona, request, "add")
                        return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'existe_inscripcion_activa':
            try:
                # if 'id' in request.POST:
                #     inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                #     if RegistrarPrestamoLibro.objects.filter(status=True, inscripcion=inscripcion, fecha=datetime.now().date(), horafin__isnull=True).exists():
                #         return JsonResponse({"result": "ok", "existe": True, "mensaje": inscripcion.persona.nombre_completo_inverso()+', ya se encuentra registrado el dia de hoy...'})
                #     else:
                return JsonResponse({"result": "ok", "existe": False})
                # else:
                #     return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'existe_inscripcion_activa_externo':
            try:
                # if 'id' in request.POST:
                #     persona = Persona.objects.get(pk=int(request.POST['id']))
                #     if RegistrarPrestamoLibro.objects.filter(status=True, persona=persona, fecha=datetime.now().date(), horafin__isnull=True).exists():
                #         return JsonResponse({"result": "ok", "existe": True, "mensaje": persona.nombre_completo_inverso()+', ya se encuentra registrado el dia de hoy...'})
                #     else:
                return JsonResponse({"result": "ok", "existe": False})
                # else:
                #     return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delvisita':
            try:
                visita = RegistrarPrestamoLibro.objects.get(pk=int(request.POST['id']))
                log(u'Elimino el registro prestamo libro CRAI: %s' % visita.persona if visita.persona else visita.inscripcion.persona, request, "add")
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
                    data['cantidad_estudiantes'] = cant_est =  RegistrarVisitaGymUmeni.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True).count()
                    data['cantidad_administrativo'] =cant_adm =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True).count()
                    data['cantidad_docententes'] = cant_doc =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True).count()
                    data['cantidad_trabajadores'] = cant_tra =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True).count()
                    data['total'] = cant_est + cant_adm + cant_doc + cant_tra
                    return conviert_html_to_pdf(
                        'adm_gimnasio/reportegeneral_pdf.html',
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
                            data['administrativos'] = administradores = RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        elif int(request.POST['tipo']) == 2:
                            data['trabajadores'] = trabajadores = RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        elif int(request.POST['tipo']) == 3:
                            data['docentes'] = docentes = RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])),status=True)
                        else:
                            data['estudiantes'] = estudiantes = RegistrarVisitaGymUmeni.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])),status=True)
                    else:
                        data['fecha'] = datetime.now().date()
                        data['estudiantes'] = estudiantes =  RegistrarVisitaGymUmeni.objects.filter(persona__isnull=True, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True)
                        data['administrativos'] = administradores =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status= True)
                        data['docentes'] = docentes =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)
                        data['trabajadores'] = trabajadores =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, fecha__range=(convertir_fecha(request.POST['de']), convertir_fecha(request.POST['hasta'])), status=True)

                else:
                    if 'tipo' in request.POST and int(request.POST['tipo'])>0:
                        if int(request.POST['tipo']) == 1:
                            data['administrativos'] = administradores = RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, status=True)
                        elif int(request.POST['tipo']) == 2:
                            data['trabajadores'] = trabajadores = RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, status=True)
                        elif int(request.POST['tipo']) == 3:
                            data['docentes'] = docentes = RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, status=True)
                        else:
                            data['estudiantes'] = estudiantes = RegistrarVisitaGymUmeni.objects.filter(persona__isnull=True, status=True)
                    else:
                        data['estudiantes'] = estudiantes =  RegistrarVisitaGymUmeni.objects.filter(persona__isnull=True, status= True)
                        data['administrativos'] = administradores =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=1, status= True)
                        data['docentes'] = docentes =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=2, status=True)
                        data['trabajadores'] = trabajadores =  RegistrarVisitaGymUmeni.objects.filter(inscripcion__isnull=True, regimenlaboral__id=3, status=True)
                data['tipo'] = int(request.POST['tipo'])
                data['fecha'] = datetime.now().date()
                return conviert_html_to_pdf(
                    'adm_gimnasio/reporte_pdf.html',
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
                    visita = RegistrarPrestamoLibro.objects.get(pk=int(request.POST['id']))
                    visita.horafin = datetime.now().today()
                    visita.save(request)
                    log(u'Registro hora de salida prestamo libro del CRAI: %s' % visita.persona if visita.persona else visita.inscripcion.persona, request, "add")
                    return JsonResponse({"result": "ok", "horafin": visita.horafin.strftime("%Y-%m-%d %H:%M ")})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al registrar hora salida."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addexterno':
            try:
                f = ClienteExternoCraiForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['cedula'] and Persona.objects.filter(cedula=f.cleaned_data['cedula']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El numero de cedula ya esta registrado."})
                    clienteexterno = Persona(nombres=f.cleaned_data['nombres'],
                                             apellido1=f.cleaned_data['apellido1'],
                                             apellido2=f.cleaned_data['apellido2'],
                                             cedula=f.cleaned_data['cedula'],
                                             sexo=f.cleaned_data['sexo'],
                                             tipopersona=1,
                                             direccion=f.cleaned_data['direccion'],
                                             direccion2=f.cleaned_data['direccion2'],
                                             nacimiento=datetime.now().date())
                    clienteexterno.save(request)
                    externo = Externo(persona=clienteexterno)
                    externo.save(request)
                    clienteexterno.crear_perfil(externo=externo)
                    clienteexterno.mi_perfil()
                    log(u'Adiciono cliente externo: %s' % clienteexterno, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addinscripcion':
                try:
                    data['title'] = u'Registrar Prestamo Libro CRAI Unemi'
                    data['s'] = request.GET['s']
                    data['id'] = request.GET['id']
                    data['idm'] = request.GET['idm']
                    form = RegistrarPrestamoLibroForm()
                    data['form'] = form
                    return render(request, "adm_bibliotecacrai/addinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'addinscripcionexterno':
                try:
                    data['title'] = u'Registrar Prestamo Libro CRAI Unemi'
                    data['s'] = request.GET['s']
                    data['id'] = request.GET['id']
                    form = RegistrarPrestamoLibroForm()
                    data['form'] = form
                    return render(request, "adm_bibliotecacrai/addinscripcionexterno.html", data)
                except Exception as ex:
                    pass

            if action == 'delvisita':
                try:
                    data['title'] = u'Eliminar Registro Ingreso'
                    data['visita'] =  RegistrarPrestamoLibro.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_bibliotecacrai/delvisita.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrarinscripcion':
                data['title'] = u'Listado de estudiantes UNEMI'
                try:
                    search = None
                    ids = None
                    inscripciones = []
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            inscripciones = Inscripcion.objects.filter(Q(persona__nombres__icontains=search) |
                                                                       Q(persona__apellido1__icontains=search) |
                                                                       Q(persona__apellido2__icontains=search) |
                                                                       Q(persona__cedula__icontains=search) |
                                                                       Q(persona__pasaporte__icontains=search) |
                                                                       Q(identificador__icontains=search) |
                                                                       Q(inscripciongrupo__grupo__nombre__icontains=search) |
                                                                       Q(persona__usuario__username__icontains=search))
                        else:
                            inscripciones = Inscripcion.objects.filter((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1])) | (
                                Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])))

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
                    data['periodos_id'] = Periodo.objects.values_list('id', flat=True).filter(status=True, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date())
                    return render(request, "adm_bibliotecacrai/view_registrarinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrarexternos':
                try:
                    data['title'] = u'Listado de personal externo UNEMI'
                    search = None
                    ids = None
                    # unemiper = RegistrarPrestamoLibro.objects.values_list('persona_id', flat=True).filter(status=True, persona__isnull=False, fecha=datetime.now().date(), horafin__isnull=True)
                    # listadist = []
                    # for gym in unemiper:
                    #     listadist.append(DistributivoPersona.objects.filter(status= True, persona=gym.persona, regimenlaboral=gym.regimenlaboral, estadopuesto__id=PUESTO_ACTIVO_ID)[0].id)
                    externos = []
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            externos = Externo.objects.filter((Q(persona__nombres__icontains=search) |
                                                               Q(persona__apellido1__icontains=search) |
                                                               Q(persona__apellido2__icontains=search) |
                                                               Q(persona__cedula__icontains=search) |
                                                               Q(persona__pasaporte__icontains=search)))
                        else:
                            externos = Externo.objects.filter((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1]) |
                                                               Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])))
                    # elif 'id' in request.GET:
                    #     externos = DistributivoPersona.objects.filter(Q(pk=int(request.GET['id']))& Q(estadopuesto__id=PUESTO_ACTIVO_ID) & (Q(regimenlaboral__id=1) | Q(regimenlaboral__id=2)|Q(regimenlaboral__id=4)))
                    # else:
                    #     externos = DistributivoPersona.objects.filter(Q(estadopuesto__id=PUESTO_ACTIVO_ID) & (Q(regimenlaboral__id=1)|Q(regimenlaboral__id=2)|Q(regimenlaboral__id=4))).exclude(id__in=listadist)

                    paging = MiPaginador(externos, 15)
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
                    data['externos'] = page.object_list
                    return render(request, "adm_bibliotecacrai/view_registrarexternos.html", data)
                except Exception as ex:
                    pass

            elif action == 'verhistorial':
                data['title'] = u'Control de Prestamos Libro CRAI UNEMI (Historial)'
                try:
                    search = None
                    ids = None
                    fecha = None
                    visitas = []
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if 'fecha' in request.GET:
                            fecha = convertir_fecha(request.GET['fecha'])
                            if len(ss) == 1:
                                visitas = RegistrarPrestamoLibro.objects.filter(Q(status=True),
                                                                              ((Q(persona__nombres__icontains=search) |
                                                                                Q(persona__apellido1__icontains=search) |
                                                                                Q(persona__apellido2__icontains=search) |
                                                                                Q(persona__cedula__icontains=search)) | (
                                                                                           Q(inscripcion__persona__nombres__icontains=search) |
                                                                                           Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                           Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                           Q(inscripcion__persona__cedula__icontains=search))),
                                                                              Q(fecha=convertir_fecha(request.GET['fecha']))).exclude(horafin__isnull=True).order_by('horainicio')
                            else:
                                visitas = RegistrarPrestamoLibro.objects.filter(Q(status=True),
                                                                              (((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[0])) |
                                                                                (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))) | ((Q(inscripcion__persona__nombres__icontains=ss[0]) & Q(inscripcion__persona__nombres__icontains=ss[1])) |
                                                                                       (Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(inscripcion__persona__apellido2__icontains=ss[1])))), Q(fecha=convertir_fecha(request.GET['fecha']))).exclude(horafin__isnull=True).order_by('horainicio')
                        else:
                            if len(ss) == 1:
                                visitas = RegistrarPrestamoLibro.objects.filter(Q(status=True),
                                                                              ((Q(persona__nombres__icontains=search) |
                                                                                Q(persona__apellido1__icontains=search) |
                                                                                Q(persona__apellido2__icontains=search) |
                                                                                Q(persona__cedula__icontains=search)) | (
                                                                                           Q(inscripcion__persona__nombres__icontains=search) |
                                                                                           Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                           Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                           Q(inscripcion__persona__cedula__icontains=search)))).exclude(horafin__isnull=True).order_by('horainicio')
                            else:
                                visitas = RegistrarPrestamoLibro.objects.filter(Q(status=True),
                                                                              (((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[0])) |
                                                                                (Q(persona__apellido1__icontains=ss[0]) & Q(
                                                                                    persona__apellido2__icontains=ss[1]))) | (
                                                                                       (Q(inscripcion__persona__nombres__icontains=ss[0]) & Q(inscripcion__persona__nombres__icontains=ss[1])) |
                                                                                       (Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(inscripcion__persona__apellido2__icontains=ss[1]))))).exclude(horafin__isnull=True).order_by('horainicio')
                    elif 'fecha' in request.GET:
                        visitas = RegistrarPrestamoLibro.objects.filter(status=True, fecha=convertir_fecha(request.GET['fecha'])).exclude(horafin__isnull=True).order_by('horainicio')
                        fecha = convertir_fecha(request.GET['fecha'])
                    # else:
                    #     visitas = RegistrarIngresoCrai.objects.filter(status=True).exclude(horafin__isnull=False).order_by('-fecha', '-horainicio')
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
                    return render(request, "adm_bibliotecacrai/verhistorial.html", data)
                except Exception as ex:
                    pass

            if action == 'addexterno':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Adicionar Clientes Externos'
                    form = ClienteExternoCraiForm()
                    data['form'] = form
                    return render(request, "adm_bibliotecacrai/addexterno.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Control de Prestamos Libro CRAI UNEMI'
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
                            visitas = RegistrarPrestamoLibro.objects.filter(Q(status=True), ((Q(persona__nombres__icontains=search) |
                                                                                               Q(persona__apellido1__icontains=search) |
                                                                                               Q(persona__apellido2__icontains=search) |
                                                                                               Q(persona__cedula__icontains=search))|(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__cedula__icontains=search))), Q(fecha=convertir_fecha(request.GET['fecha']))).exclude(horafin__isnull=False).order_by('-horainicio')
                        else:
                            visitas = RegistrarPrestamoLibro.objects.filter(Q(status=True),
                                                                             (((Q(persona__nombres__icontains=ss[0])& Q(persona__nombres__icontains=ss[0])) |
                                                                               (Q(persona__apellido1__icontains=ss[0]) &Q(persona__apellido2__icontains=ss[1]))) | (
                                                                                  (Q(inscripcion__persona__nombres__icontains=ss[0])& Q(inscripcion__persona__nombres__icontains=ss[1]))|
                                                                                  (Q(inscripcion__persona__apellido1__icontains=ss[0]) &Q(inscripcion__persona__apellido2__icontains=ss[1]))
                                                                              )), Q(fecha=convertir_fecha(request.GET['fecha']))).exclude(horafin__isnull=False).order_by('-horainicio')
                    else:
                        if len(ss) == 1:
                            visitas = RegistrarPrestamoLibro.objects.filter(Q(status=True), ((Q(persona__nombres__icontains=search) |
                                                                                               Q(persona__apellido1__icontains=search) |
                                                                                               Q(persona__apellido2__icontains=search) |
                                                                                               Q(persona__cedula__icontains=search))|(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                                                                      Q(inscripcion__persona__cedula__icontains=search)))).exclude(horafin__isnull=False).order_by('-horainicio')
                        else:
                            visitas = RegistrarPrestamoLibro.objects.filter(Q(status=True),
                                                                             (((Q(persona__nombres__icontains=ss[0])& Q(persona__nombres__icontains=ss[0])) |
                                                                               (Q(persona__apellido1__icontains=ss[0]) &Q(persona__apellido2__icontains=ss[1]))) | (
                                                                                  (Q(inscripcion__persona__nombres__icontains=ss[0])& Q(inscripcion__persona__nombres__icontains=ss[1]))|
                                                                                  (Q(inscripcion__persona__apellido1__icontains=ss[0]) &Q(inscripcion__persona__apellido2__icontains=ss[1]))
                                                                              ))).exclude(horafin__isnull=False).order_by('-horainicio')
                elif 'fecha' in request.GET:
                    visitas = RegistrarPrestamoLibro.objects.filter(status=True, fecha=convertir_fecha(request.GET['fecha'])).exclude(horafin__isnull=False).order_by('-horainicio')
                    fecha = convertir_fecha(request.GET['fecha'])
                else:
                    visitas = RegistrarPrestamoLibro.objects.filter(status=True).exclude(horafin__isnull=False).order_by('-fecha','-horainicio')
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
                return render(request, "adm_bibliotecacrai/view.html", data)
            except Exception as ex:
                pass


