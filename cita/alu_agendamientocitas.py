# -*- coding: UTF-8 -*-
import json
import calendar
from datetime import datetime, timedelta, date

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render
from django.contrib import messages

from decorators import secure_module, last_access

from cita.forms import *
from cita.models import *
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, notificacion
from django.db.models import Q
from sga.templatetags.sga_extras import encrypt
from cita.funciones import turnosdisponible
from sga.funcionesxhtml2pdf import conviert_html_to_2pdf

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
# @transaction.atomic()
def view(request):
    data = {}
    hoy = datetime.now().date()
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        action = request.POST['action']

        # Servicios
        if action == 'addcita':
            with transaction.atomic():
                try:
                    fecha = datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date()
                    estado = 1
                    idservicio = int(encrypt(request.POST['idservicio']))
                    lista = json.loads(request.POST['listahorarios'])
                    # servicio = ServicioConfigurado.objects.get(pk=idservicio)

                    if not request.POST['horario']:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Seleccione un horario a reservar."})
                    horario = HorarioServicioCita.objects.get(id=request.POST['horario'])
                    # Validar si existe ocupado servicio

                    if not turnosdisponible(horario,fecha):
                        messages.error(request,'Esta cita ha sido agendada por otro usuario.')
                        return JsonResponse({"result": False,'funcion':True})
                        #raise NameError(")
                    if horario.requisitos_archivo().filter(opcional=False):
                        estado = 0
                    tipo_atencion = horario.tipo_atencion
                    if horario.tipo_atencion == 0:
                        tipo_atencion = int(request.POST['tipo_atencion'])
                    turno = horario.generar_turno(persona)
                    familiar = None
                    paraFamiliar = False
                    if 'esFamiliar' in request.POST:
                        paraFamiliar = True
                        idFamiliar = int(request.POST['familiar'])
                        familiar = PersonaDatosFamiliares.objects.get(id=idFamiliar)

                    cita = PersonaCitaAgendada(persona=persona,
                                               persona_responsable=horario.responsableservicio.responsable,
                                               servicio_id=idservicio,
                                               horario=horario,
                                               estado=estado,
                                               perfil=perfilprincipal,
                                               codigo=turno,
                                               espersonal=paraFamiliar,
                                               familiar=familiar,
                                               fechacita=fecha,
                                               tipo_atencion=tipo_atencion)
                    cita.save(request)
                    # Guardo informacion de historial de agendamiento cita
                    historial = HistorialSolicitudCita(cita=cita, estado_solicitud=cita.estado,
                                                       observacion='Creación de cita')
                    historial.save(request)
                    # Algoritmo de guardado de documentos requeridos
                    totalsubidos = 0
                    requisitos_solicitados = horario.requisitos_archivo()
                    for rs in requisitos_solicitados:
                        if 'doc_{}'.format(rs.requisito.nombre_input()) in request.FILES:
                            totalsubidos += 1
                        elif rs.opcional:
                            totalsubidos += 1
                    if not totalsubidos == len(requisitos_solicitados):
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Debe subir todos los requisitos solicitados."},
                                            safe=False)
                    for rs in requisitos_solicitados:
                        docrequerido = DocumentosSolicitudServicio(cita=cita, requisito=rs, estados=0)
                        docrequerido.save(request)
                        if 'doc_{}'.format(rs.requisito.nombre_input()) in request.FILES:
                            newfile = request.FILES['doc_{}'.format(rs.requisito.nombre_input())]
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                            if not exte.lower() in ['pdf']:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})
                            # nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
                            newfile._name = generar_nombre(
                                "Requisito_servicio_{}_{}".format(rs.pk, random.randint(1, 100000).__str__()),
                                newfile._name)
                            docrequerido.archivo = newfile
                            docrequerido.obligatorio = True if not rs.opcional else False
                            docrequerido.save(request)
                            # Historial de documentos de cita
                            historial = HistorialSolicitudCita(cita=cita, documento=docrequerido,
                                                               estado_solicitud=cita.estado,
                                                               observacion='Creación documento de solicitud')
                            historial.save(request)

                    servicio = cita.servicio.serviciocita.nombre.lower()
                    titulo = u"Agendamiento de cita en {} ({} | {})".format(servicio, cita.fechacita,
                                                                            cita.horario.turno.nombre_horario())
                    mensaje = 'Su cita fue agendada satisfactoriamente.'
                    lista_email = cita.persona.lista_emails()
                    # lista_email = ['jguachuns@unemi.edu.ec', ]
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': datetime.now().date(),
                                   'hora': datetime.now().time(),
                                   'subcita': cita,
                                   'persona': cita.persona,
                                   'mensaje': mensaje, }
                    template = "emails/notificacion_agendamientocitas.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])

                    lista_email = cita.persona_responsable.lista_emails()
                    # lista_email = ['jguachuns@unemi.edu.ec', ]
                    mensaje = f'Una cita fue agendada por {cita.persona.nombre_completo_minus()} para su atención.'
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': datetime.now().date(),
                                   'hora': datetime.now().time(),
                                   'subcita': cita,
                                   'persona': cita.persona_responsable,
                                   'mensaje': mensaje}
                    template = "emails/notificacion_admin_agendamientocitas.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])

                    log(u'{} : Inicio Agendamiento de Cita  {}'.format(persona,
                                                                       horario.responsableservicio.servicio.__str__()),
                        request, "addcita")
                    url_ = '{}?action=miscitas'.format(request.path)
                    return JsonResponse({"result": False, "to": url_})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delcita':
            with transaction.atomic():
                try:
                    instancia = PersonaCitaAgendada.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.estado = 2
                    instancia.save(request)

                    historial = HistorialSolicitudCita(cita=instancia, estado_solicitud=instancia.estado,
                                                       observacion='Anulación de cita')
                    historial.save(request)
                    log(u'Elimino citas de servicio: %s' % instancia, request, "delcita")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'subirrequisito':
            with transaction.atomic():
                try:
                    instance = DocumentosSolicitudServicio.objects.get(pk=int(request.POST['id']))
                    form = SubirRequisitoForm(request.POST, request.FILES)
                    if form.is_valid() and form.validador(instance.estados):
                        cita = instance.cita
                        beneficiario = cita.persona.nombre_normal_minus()
                        requisito_ = instance.requisito.requisito.nombre.capitalize()
                        titulo = u"Documento de cita agendada ({})".format('Subido')
                        mensaje = 'Documento {} fue subido por el usuario {}'.format(requisito_, beneficiario)
                        if instance.estados == 2:
                            instance.estados = 4
                            titulo = u"Documento de cita agendada ({})".format(instance.get_estados_display())
                            mensaje = 'Documento {} fue corregido por el usuario {}'.format(requisito_, beneficiario)

                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 2194304:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                            if not exte.lower() in ['pdf']:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})
                            newfile._name = generar_nombre(
                                "Requisito_servicio_{}_{}".format(instance.pk, random.randint(1, 100000).__str__()),
                                newfile._name)
                            instance.archivo = newfile
                            instance.save(request)

                        if cita.doc_validacion() == 0:
                            if cita.subcitas_exits():
                                cita.estado = 6
                            else:
                                cita.estado = 0
                            cita.save(request)

                        # Guardo informacion de historial de agendamiento cita
                        historial = HistorialSolicitudCita(cita=instance.cita, documento=instance,
                                                           estado_documento=instance.estados,
                                                           estado_solicitud=instance.cita.estado,
                                                           observacion='Edita archivo')
                        historial.save(request)
                        notificacion(titulo, mensaje, cita.persona_responsable, None,
                                     f'/adm_gestorcitas?&s={cita.codigo}',
                                     instance.pk, 1, 'sga', DocumentosSolicitudServicio, request)
                        titulo = titulo
                        lista_email = cita.persona_responsable.lista_emails()
                        # lista_email = ['jguachuns@unemi.edu.ec', ]
                        datos_email = {'sistema': request.session['nombresistema'],
                                       'fecha': datetime.now().date(),
                                       'hora': datetime.now().time(),
                                       'documento': instance,
                                       'estado': instance.get_estados_display(),
                                       'persona': cita.persona_responsable,
                                       'mensaje': mensaje}
                        template = "emails/notificacion_admin_agendamientocitas.html"
                        send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    diccionario = {'id': instance.id, 'url_pdf': instance.archivo.url,
                                   'estado': instance.get_estados_display(), 'idestado': instance.estados,
                                   'color': instance.color_estado()}
                    log(u'Valido documento de cita: %s' % instance, request, "edit")
                    return JsonResponse(
                        {'result': True, 'data_return': True, 'mensaje': u'Guardado con exito', 'data': diccionario},
                        safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde.".format(str(ex))}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            # Agendar Cita
            if action == 'agendar':
                try:
                    data['title'] = 'Agendar Cita'
                    data['servicio'] = ServicioConfigurado.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, 'alu_agendamientocitas/viewagendar.html', data)
                except Exception as ex:
                    pass

            if action == 'cargarturno':
                try:
                    idresponsableservicio = request.GET['idpersona']
                    lista = json.loads(request.GET['listahorarios'])

                    fecha = request.GET['fecha']

                    horarios = HorarioServicioCita.objects.filter(id__in=lista,responsableservicio_id=idresponsableservicio, status=True, mostrar=True)
                    horarios_disponibles = []

                    for horario in horarios:
                        turnos_disponibles = horario.citas_disponibles(fecha)
                        if turnos_disponibles > 0:
                            disponible = horario.horario_disponible(fecha)
                            if disponible:
                                horarios_disponibles.append({
                                    'id': horario.id,
                                    'nombre_horario': horario.turno.nombre_horario(),
                                    'id_tipo_atencion': horario.tipo_atencion,
                                    'tipo_atencion': horario.get_tipo_atencion_display(),
                                    'turnos': turnos_disponibles,
                                })

                    return JsonResponse({'result': 'ok', 'horarios': horarios_disponibles})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

            if action == 'cargarcalendario':
                try:
                    fecha = datetime.now().date()
                    panio = fecha.year
                    pmes = fecha.month
                    if 'mover' in request.GET:
                        mover = request.GET['mover']

                        if mover == 'anterior':
                            mes = int(request.GET['mes'])
                            anio = int(request.GET['anio'])
                            pmes = mes - 1
                            if pmes == 0:
                                pmes = 12
                                panio = anio - 1
                            else:
                                panio = anio

                        elif mover == 'proximo':
                            mes = int(request.GET['mes'])
                            anio = int(request.GET['anio'])
                            pmes = mes + 1
                            if pmes == 13:
                                pmes = 1
                                panio = anio + 1
                            else:
                                panio = anio

                    id = int(encrypt(request.GET['idservicio']))
                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listahorarios = []
                    data['servicio'] = servicio = ServicioConfigurado.objects.get(pk=id)
                    # finicio = hoy - timedelta(days=servicio.numdias)
                    data['horarios'] = horarios = HorarioServicioCita.objects.filter(status=True,
                                                                                     responsableservicio__servicio_id=id,
                                                                                     mostrar=True,
                                                                                     fechafin__gte=hoy,
                                                                                     # fechainicio__gte=finicio
                                                                                     )
                    h_fecha = horarios.order_by('fechainicio').first()
                    diasreservainicio = servicio.numdiasinicio
                    if servicio.prioridad != 1:
                        diasreserva = servicio.numdias + diasreservainicio
                        anio_actual = hoy.year
                        if hoy.month != s_mes:
                            anioubicado = s_anio
                            cont = 0
                            while anioubicado >= anio_actual:
                                iden = True
                                if anio_actual == anioubicado and cont == 0:
                                    mes = hoy.month
                                    mesubicado = s_mes
                                elif anio_actual == anioubicado:
                                    mes = hoy.month
                                    mesubicado = 12
                                elif anio_actual < anioubicado and cont == 0:
                                    mes = 0
                                    mesubicado = s_mes
                                elif anio_actual < anioubicado:
                                    mes = 0
                                    mesubicado = 12
                                while mesubicado > mes:
                                    if anio_actual < anioubicado and iden:
                                        mes = 1
                                        iden = False
                                    numsinhorario = 0
                                    msiguiente = calendar.monthrange(s_anio, mes)
                                    rango = range(1, int(msiguiente[1] + 1), 1)
                                    if mes == hoy.month:
                                        rango = range(int(hoy.day), int(msiguiente[1] + 1), 1)
                                    for dia in rango:
                                        ban = False
                                        fecha = date(s_anio, mes, dia)
                                        numdia = fecha.weekday() + 1
                                        for horario in horarios:
                                            if horario.dia == numdia and h_fecha.fechainicio <= fecha:
                                                ban = True
                                        if ban == False:
                                            numsinhorario += 1
                                    diasreserva += numsinhorario
                                    if mes == hoy.month:
                                        diasreserva -= msiguiente[1] - (hoy.day - 1)
                                    else:
                                        diasreserva = diasreserva - msiguiente[1]

                                    mes += 1
                                cont += 1
                                anioubicado -= 1

                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        lista.update(dia)
                    comienzo = False
                    fin = False
                    for i in lista.items():
                        try:
                            fecha = date(s_anio, s_mes, s_dia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(s_anio, s_mes, s_dia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: s_dia}
                            lista.update(dia)
                            listhorario = []
                            sinhorario = True
                            puedereservar = False
                            numerodia = fecha.weekday() + 1
                            if fecha >= hoy:
                                turnos = 0
                                listturnos = []
                                for horario in horarios:
                                    if horario.dia == numerodia and fecha <= horario.fechafin and fecha >= horario.fechainicio:
                                        listhorario.append(horario.id)
                                if listhorario:
                                    sinhorario = False
                                    filter = horarios.filter(status=True, pk__in=listhorario)
                                    for horario in filter:
                                        listturnos.append(horario.turno.comienza)
                                        turnos += horario.citas_disponibles(fecha)

                                monthRange = calendar.monthrange(s_anio, s_mes)
                                if servicio.prioridad != 1:
                                    if diasreserva > 0 and s_dia <= monthRange[1] and not sinhorario:
                                        ordenadas = []
                                        ordenadas = sorted(listturnos, reverse=True)
                                        if ordenadas[0] > datetime.now().time() or fecha > datetime.now().date():
                                            puedereservar = True
                                            diasreserva -= 1
                                else:
                                    if s_dia <= monthRange[1] and not sinhorario:
                                        ordenadas = []
                                        ordenadas = sorted(listturnos, reverse=True)
                                        if ordenadas[0] > datetime.now().time() or fecha > datetime.now().date():
                                            puedereservar = True
                                diccionario = {'dia': s_dia, 'turnos': turnos, 'listahorario': listhorario,
                                               'sinhorario': sinhorario, 'fecha': fecha, 'puedereservar': puedereservar}
                                listahorarios.append(diccionario)
                            s_dia += 1

                    if horarios:
                        data['ultimafecha'] = ultimafecha = horarios.order_by('fechafin').last().fechafin
                        primerafecha = horarios.order_by('fechafin').first().fechafin
                        anio = primerafecha.year
                        rango = ultimafecha.year - primerafecha.year
                        for i in range(0, rango, 1):
                            if s_anio == anio + (i + 1):
                                anio = s_anio
                        data['year'] = anio
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['hoy'] = hoy
                    data['hoy_dia'] = hoy.day + diasreservainicio
                    data['hoy_mes'] = hoy.month
                    data['listahorarios'] = listahorarios
                    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
                    data['fechaactual'] = date(hoy.year, hoy.month, ultimo_dia)
                    data['fechacalendario'] = date(s_anio, s_mes, s_dia - 1)
                    template = get_template("alu_agendamientocitas/viewcalendario.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": 'bad', 'mensaje': 'Error'.format(ex)})

            if action == 'addcita':
                try:
                    servicio = ServicioConfigurado.objects.get(pk=int(encrypt(request.GET['idservicio'])))
                    if servicio.existe_cita_agendada(persona):
                        return JsonResponse({"result": False, "agendado": True,
                                             "mensaje": u"Usted ya cuenta con una cita agendada de esta servicio, "
                                                        u"por favor finalice o cancele la pendiente para iniciar otra."})

                    data['horariosid'] = horariosid = json.loads(request.GET["listaid[]"])

                    data['fecha'] = request.GET['fecha']
                    data['servicio'] = servicio


                    data['responsables'] = horario = HorarioServicioCita.objects.filter(id__in=horariosid,
                                                                                        status=True).values_list(
                        'responsableservicio_id',
                        'responsableservicio__responsable__nombres',
                        'responsableservicio__responsable__apellido1',
                        'responsableservicio__responsable__apellido2').distinct('responsableservicio_id')
                    data['horariodia'] = HorarioServicioCita.objects.filter(id__in=horariosid, status=True).order_by(
                        'turno__comienza').first()

                    template = get_template("alu_agendamientocitas/formagendar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': 'Error'.format(ex)})

            if action == 'listfamiliar':
                try:
                    lista = []
                    id = int(request.GET['id'])
                    familiares = PersonaDatosFamiliares.objects.filter(status=True, persona_id=id)
                    for f in familiares:
                        text = str(f.nombre)
                        lista.append({'value': f.id, 'text': text})
                    return JsonResponse({'result': True, 'data': lista})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            # Historial de citas agendadas
            if action == 'miscitas':
                try:
                    data['servicios'] = PersonaCitaAgendada.objects.filter(persona = persona, status = True, estado__in=[5,6])\
                                         .values_list('servicio__serviciocita_id','servicio__serviciocita__nombre')\
                                         .order_by('servicio__serviciocita_id').distinct()
                    data['title'] = u'Citas'
                    filtro = request.GET.get('f', '')
                    search, filtros, url_vars = request.GET.get('search', ''), \
                        Q(status=True, persona=persona), \
                        f'&action={action}'
                    request.session['viewactivo'] = 1
                    if filtro == 'progreso':
                        filtros = filtros & Q(fechacita__gte=hoy, estado__in=[0, 1, 3, 6], )
                        request.session['viewactivo'] = 2
                    elif filtro == 'finalizado':
                        filtros = filtros & Q(fechacita__lt=hoy, estado=5)
                        request.session['viewactivo'] = 3
                    elif filtro == 'anulado':
                        filtros = filtros & Q(estado=2)
                        request.session['viewactivo'] = 4

                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (
                                    Q(codigo__unaccent__icontains=search) |
                                    Q(horario__responsableservicio__servicio__serviciocita__nombre__unaccent__icontains=search))
                        else:
                            filtros = filtros & (
                                    Q(horario__responsableservicio__servicio__serviciocita__nombre__unaccent__icontains=s[0]) &
                                    Q(horario__responsableservicio__servicio__serviciocita__nombre__unaccent__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    if filtro != '':
                        url_vars += '&f={}'.format(filtro)
                    reservas = PersonaCitaAgendada.objects.filter(filtros).order_by('-pk')
                    paging = MiPaginador(reservas, 5)
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
                    data["url_vars"] = url_vars
                    data['filtro'] = filtro
                    data['listado'] = page.object_list
                    return render(request, 'alu_agendamientocitas/viewmiscitas.html', data)
                except Exception as ex:
                    pass

            if action == 'reporte_asistenciausuario':
                try:
                    idservicios=request.GET.getlist('idservicio')
                    data["servicios_agendados"] = servicios_agendados = PersonaCitaAgendada.objects.filter(persona=persona, status=True,servicio__serviciocita_id__in=idservicios)
                    data["hoy"] =hoy
                    data["persona"] =persona
                    template = 'adm_agendamientocitas/modal/pdfasistenciaservicio.html'
                    #return JsonResponse({"result": True, 'data': template.render(data)})
                    qrname = 'Historial_Asistencia{}'.format(random.randint(1, 100000).__str__())
                    return conviert_html_to_2pdf(template, {'pagesize': 'A4','data': data}, qrname)
                except Exception as ex:
                    pass

            if action == 'requisitos':
                try:
                    form = SubirRequisitoForm()
                    data['form'] = form
                    data['cita'] = PersonaCitaAgendada.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("alu_agendamientocitas/modal/formrequisitos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'subcitas':
                try:
                    data['cita'] = cita = PersonaCitaAgendada.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['subcitas'] = cita.subcitas()
                    template = get_template("alu_agendamientocitas/modal/subcitas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Agendamiento de citas'
                # ids=[]
                # horarios=HorarioServicioCita.objects.filter(status=True, mostrar=True).order_by('responsableservicio__servicio_id').distinct('responsableservicio__servicio_id')
                ids = HorarioServicioCita.objects.filter(status=True, mostrar=True, fechafin__gte=hoy).distinct(
                    'responsableservicio__servicio_id').values_list('responsableservicio__servicio_id')
                # for horario in horarios:
                #     if horario.fechafin >= hoy:
                #         ids.append(horario.responsableservicio.servicio.id)

                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, serviciocita__mostrar=True,
                                                                       serviciocita__status=True,
                                                                       serviciocita__departamentoservicio__status=True,
                                                                       mostrar=True, id__in=ids, soloadministrativo=False), ''
                if search:
                    filtro = filtro & (Q(serviciocita__nombre__unaccent__icontains=search))
                    url_vars += '&s=' + search
                    data['s'] = search

                listado = ServicioConfigurado.objects.filter(filtro).order_by('id')
                paging = MiPaginador(listado, 12)
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
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['listcount'] = len(listado)
                return render(request, 'alu_agendamientocitas/view.html', data)
            except Exception as ex:
                return render({'result': False, 'mensaje': '{}'.format(ex)})
