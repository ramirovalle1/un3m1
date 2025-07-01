# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import last_access, secure_module
from sga.commonviews import adduserdata
from sga.forms import SolicitudAperturaClaseForm
from sga.funciones import log, generar_nombre, variable_valor, convertir_fecha
from sga.models import SolicitudAperturaClase, Materia, Turno, LeccionGrupo, DiasNoLaborable, Leccion, ProfesorMateria, \
    ProfesorDistributivoHoras, Clase, ClaseAsincronica, TipoProfesor


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor,status=True).exists() else None
    # if distributivo.periodo.id not in (85, 82):
    #     return HttpResponseRedirect("/?info=No disponible por el momento.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                if 'documento' in request.FILES:
                        newfile = request.FILES['documento']
                        if newfile.size > 5242880:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 4Mb"})
                f = SolicitudAperturaClaseForm(request.POST, request.FILES)
                if f.is_valid():
                    materia = f.cleaned_data['materia']
                    if int(f.cleaned_data['tipo']) == 2:
                        tiposolicitud = int(f.cleaned_data['tiposolicituddiferido'])
                    else:
                        tiposolicitud = int(f.cleaned_data['tiposolicitudinconveniente'])
                    fecha = f.cleaned_data['fecha']

                    if tiposolicitud == 4:
                        fechahasta = f.cleaned_data['fechahasta']
                    else:
                        fechahasta = f.cleaned_data['fecha']

                    fechasrango = []
                    if fecha == fechahasta:
                        fechasrango.append(fecha)
                    else:
                        for dia in daterange(fecha, (fechahasta + timedelta(days=1))):
                            if not DiasNoLaborable.objects.filter(periodo=periodo, fecha=dia).exists():
                                fechasrango.append(dia)
                    CANTIDAD_DIAS_APERTURAR_CLASE = variable_valor('CANTIDAD_DIAS_APERTURAR_CLASE')
                    if (fecha + timedelta(days=CANTIDAD_DIAS_APERTURAR_CLASE)) < datetime.now().date():
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Hasta las %s días puede solicitar apertura de clase." % CANTIDAD_DIAS_APERTURAR_CLASE })
                    if fecha > datetime.now().date():
                        return JsonResponse({"result": "bad", "mensaje": u"Error, la fecha no puede ser mayor que hoy."})
                    # if (datetime.now() - datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0)).days > CANTIDAD_DIAS_APERTURAR_CLASE:
                    #     return JsonResponse({"result": "bad", "mensaje": u"No puede justificar despues de %s dias." % CANTIDAD_DIAS_APERTURAR_CLASE})
                    if tiposolicitud == 4:
                        fechadiferido = f.cleaned_data['fechadiferido']
                        # if (fecha + timedelta(days=3)) < datetime.now().date():
                        #     return JsonResponse({"result": "bad", "mensaje": u"Error, Hasta las 72 horas puede solicitar apertura de clase."})
                        if fechahasta > datetime.now().date():
                            return JsonResponse({"result": "bad", "mensaje": u"Error, La fecha hasta no puede ser mayor que hoy."})
                        if fechadiferido < datetime.now().date(): #=
                            return JsonResponse({"result": "bad", "mensaje": u"Error, la fecha diferido no puede ser menor o igual que hoy."})
                    else:
                        # if DiasNoLaborable.objects.filter(periodo=periodo, fecha=f.cleaned_data['fecha']).exists():
                            bandera = 0
                        #     for dnl in DiasNoLaborable.objects.filter(periodo=periodo, fecha=f.cleaned_data['fecha']):
                        #         if dnl.coordinacion_id == materia.coordinacion_materia().id and dnl.carrera_id == materia.carrera().id and dnl.nivelmalla_id == materia.asignaturamalla.nivelmalla.id and dnl.fecha == f.cleaned_data['fecha']:
                        #             bandera = 1
                        #         elif dnl.coordinacion_id == materia.coordinacion_materia().id and dnl.carrera_id == materia.carrera().id and dnl.fecha == f.cleaned_data['fecha']:
                        #             bandera = 1
                        #         elif dnl.coordinacion_id == materia.coordinacion_materia().id and dnl.fecha == f.cleaned_data['fecha']:
                        #             bandera = 1
                        #         elif dnl.carrera_id == materia.carrera().id and dnl.fecha == f.cleaned_data['fecha']:
                        #             bandera = 1
                        #         elif dnl.nivelmalla_id == materia.asignaturamalla.nivelmalla.id and dnl.fecha == f.cleaned_data['fecha']:
                        #             bandera = 1
                        #         elif dnl.fecha == f.cleaned_data['fecha'] and dnl.coordinacion == None and dnl.carrera == None and dnl.nivelmalla == None:
                        #             bandera = 1
                        #     if bandera == 1:
                        #         return JsonResponse({"result": "bad", "mensaje": u"Error, Día no laborable"})
                    bandera_guardo = 0


                    for fechalista in fechasrango:
                        dia = fechalista.isoweekday()
                        bandera = 0

                        tiposprofesor = TipoProfesor.objects.filter(clase__dia=dia, clase__materia=materia, clase__activo=True, clase__profesor=profesor).values_list('id').distinct()

                        for tipoprofesor in tiposprofesor:
                            clases = Clase.objects.filter(dia=dia, materia=materia, activo=True, profesor=profesor, tipoprofesor_id=tipoprofesor).order_by("-turno_id")
                            for clase in clases:
                                bandera = 0
                                estado = 1
                                if materia.clase_set.filter(inicio__lte=fechalista, fin__gte=fechalista, dia=dia, activo=True, turno=clase.turno).exists():
                                    reemplazo = False
                                    if materia.es_profesormateria_reemplazo_pm(profesor):
                                        reemplazo = True
                                        if Leccion.objects.filter(clase__activo=True, fecha=fechalista,
                                                                  clase__materia=materia, clase__turno=clase.turno,
                                                                  clase__materia__profesormateria__profesor=materia.profesor_principal()).exists():
                                            bandera = 1
                                    else:
                                        if Leccion.objects.filter(clase__activo=True, fecha=fechalista,
                                                                  clase__materia=materia, clase__turno=clase.turno,
                                                                  clase__materia__profesormateria__profesor=materia.profesor_principal()).exists():
                                            bandera = 1
                                    if SolicitudAperturaClase.objects.filter(profesor=profesor,
                                                                             materia=materia,
                                                                             fecha=fechalista, turno=clase.turno).exists():
                                        bandera = 1

                                    if ClaseAsincronica.objects.filter(clase__materia=clase.materia,
                                                                           clase__tipoprofesor=clase.tipoprofesor,
                                                                           fechaforo=fecha, status=True).exists():
                                        bandera = 1

                                    if bandera == 0:
                                        if materia.asignaturamalla.malla.carrera.mi_coordinacion2() == 9:
                                            estado = 2

                                        if tiposolicitud != 4:
                                            solicitud = SolicitudAperturaClase(profesor=profesor,
                                                                               materia=materia,
                                                                               fecha=fechalista,
                                                                               tiposolicitud=tiposolicitud,
                                                                               motivo=f.cleaned_data['motivo'],
                                                                               turno=clase.turno,
                                                                               reemplazo=reemplazo,
                                                                               estado=estado)
                                        else:
                                            solicitud = SolicitudAperturaClase(profesor=profesor,
                                                                               materia=materia,
                                                                               fecha=fechalista,
                                                                               tiposolicitud=tiposolicitud,
                                                                               tipomotivo=f.cleaned_data['tipomotivo'],
                                                                               motivo=f.cleaned_data['motivo'],
                                                                               aula=f.cleaned_data['aula'],
                                                                               turno=clase.turno,
                                                                               reemplazo=reemplazo,
                                                                               estado=estado,
                                                                               fechadiferido=f.cleaned_data[
                                                                                   'fechadiferido'])
                                        solicitud.save(request)
                                        bandera_guardo = 1
                                        if 'documento' in request.FILES:
                                            newfile = request.FILES['documento']
                                            newfile._name = generar_nombre("aperturaclase_", newfile._name)
                                            solicitud.documento = newfile
                                            solicitud.save()

                    if bandera_guardo == 1:
                        log(u'Adiciono solicitud apertura de clase: %s' % solicitud, request, "add")
                        solicitud.enviar_correo(request.session['nombresistema'], tiposolicitud, solicitud.materia)
                    else:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"No se generero ninguna solicitud, porque en la fecha si tiene registrado asistencias o solicitudes."})
                    return JsonResponse({"result": "ok"})

                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, tipo de archivo incorrecto."})

        if action == 'delsolicitud':
            try:
                solicitud = SolicitudAperturaClase.objects.get(pk=request.POST['id'])
                log(u'Elimino solicitud de apertura de clase: %s' % solicitud, request, "del")
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'turnos':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    nlista = {}
                    for turno in Turno.objects.filter(clase__materia=materia).distinct():
                        nlista.update({turno.id: {'id': turno.id, 'nombre': turno.flexbox_repr()}})
                    return JsonResponse({'result': 'ok', 'lista': nlista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'materiasenfecha':
                try:
                    materias = []
                    tipo = int(request.POST['tipo'])
                    tiposol = int(request.POST['tiposol'])
                    if tiposol == 5:
                        fecha = convertir_fecha(request.POST['f'])
                        clases = Clase.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, activo=True, dia=fecha.isocalendar()[2]).distinct('materia', 'tipoprofesor')
                        tipoprofesor = []
                        for clase in clases:
                            tipoprofesor.append([clase.tipoprofesor.id])
                            if not ClaseAsincronica.objects.filter(clase__materia=clase.materia, clase__tipoprofesor=clase.tipoprofesor, fechaforo=fecha, status=True).exists():
                                materias.append([clase.materia.id, clase.materia.__str__()])
                    else:
                        profesormaterias = ProfesorMateria.objects.filter(activo=True, profesor=profesor, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 5, 6, 7]).distinct().order_by('desde', 'materia__asignatura__nombre')
                        if tipo == 1:
                            fecha = convertir_fecha(request.POST['f'])
                            for profesormateria in profesormaterias:
                                if profesormateria.esta_dia_con_horario(fecha):
                                    data = profesormateria.asistencia_docente(fecha, fecha, periodo)
                                    # if data['total_asistencias_no_registradas']>0:
                                    if data['total_asistencias_dias_tutoria'] > 0 or data['total_asistencias_dias_feriados'] > 0 or data['total_asistencias_dias_suspension'] > 0 or data['total_asistencias_no_registradas'] > 0 :
                                        materias.append([profesormateria.materia.id, profesormateria.materia.__str__()])
                        elif tipo == 2:
                            listasfechas = extraer_dias(convertir_fecha(request.POST['fd']), convertir_fecha(request.POST['fh']))
                            for profesormateria in profesormaterias:
                                for listafecha in listasfechas:
                                    if profesormateria.esta_dia_con_horario(listafecha):
                                        data = profesormateria.asistencia_docente(listafecha, listafecha, periodo)
                                        # if data['total_asistencias_no_registradas'] > 0:
                                        if data['total_asistencias_dias_tutoria'] > 0 or data['total_asistencias_dias_feriados'] > 0 or data['total_asistencias_dias_suspension'] > 0 or data['total_asistencias_no_registradas'] > 0 :
                                            materias.append([profesormateria.materia.id, profesormateria.materia.__str__()])
                                            break
                    return JsonResponse({'result': 'ok', 'lista': materias })
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addvideovirtual':
            try:
                solicitud= SolicitudAperturaClase.objects.get(pk=request.POST['codigosolicitud'])
                dia = int(solicitud.fecha.isocalendar()[2])
                semana = int(solicitud.fecha.isocalendar()[1])
                clase = Clase.objects.get(materia=solicitud.materia,profesor=profesor,dia=dia,turno=solicitud.turno)
                fechastr= str(solicitud.fecha)
                from Moodle_Funciones import CrearClaseVirtualClaseMoodleDiferido
                CrearClaseVirtualClaseMoodleDiferido(clase.id, persona.id, request.POST['observacion'],
                                                     request.POST['enlace2'], request.POST['enlace3'],
                                                     dia, semana,fechastr)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Nueva solicitud apertura de clase'
                    data['profesor'] = profesor
                    form = SolicitudAperturaClaseForm(initial={'fecha': datetime.now().date(),
                                                               'fechahasta': datetime.now().date(),
                                                               'fechadiferido': datetime.now().date()})
                    form.filtros(profesor, periodo)
                    data['form'] = form
                    return render(request, "pro_aperturaclase/old/addsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud apertura de clase'
                    data['solicitud'] = SolicitudAperturaClase.objects.get(pk=request.GET['id'])
                    return render(request, "pro_aperturaclase/old/delsolicitud.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Registro de Asistencias - Por inconvenientes y diferidos de clases'
            data['profesor'] = profesor
            data['solicitudes'] = profesor.solicitudaperturaclase_set.filter(materia__nivel__periodo=periodo).distinct()
            return render(request, "pro_aperturaclase/old/view.html", data)


def extraer_dias(fecha_inicio, fecha_fin):
    listafecha = []
    while fecha_inicio <= fecha_fin:
        listafecha.append(fecha_inicio)
        fecha_inicio += timedelta(days=1)
    return listafecha
