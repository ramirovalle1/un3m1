# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template import Context

from decorators import last_access, secure_module
from inno.funciones import enviar_notificacion_solicitud_registro_asistencia_pro
from inno.models import MotivoTipoInconvenienteClaseDiferido, TipoInconvenienteClaseDiferido
from sga.commonviews import adduserdata
from inno.forms import SolicitudAperturaClaseForm
from sga.funciones import log, generar_nombre, variable_valor, convertir_fecha
from sga.models import SolicitudAperturaClase, Materia, Turno, LeccionGrupo, DiasNoLaborable, Leccion, ProfesorMateria, \
    ProfesorDistributivoHoras, Clase, ClaseAsincronica, TipoProfesor, ESTADOS_PREPROYECTO, TIPO_SOLICITUDINCONVENIENTE, \
    TIPO_MOTIVO
from sga.templatetags.sga_extras import encrypt


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
    distributivo = profesor.get_distributivohoras(periodo)
    ePeriodoAcademia = periodo.get_periodoacademia()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadDataTable':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                type_request = int(request.POST['type_request']) if request.POST['type_request'] else 0
                type_motive = int(request.POST['type_motive']) if request.POST['type_motive'] else 0
                state = int(request.POST['state']) if request.POST['state'] else 0
                aaData = []
                tCount = 0
                solicitudes = profesor.solicitudaperturaclase_set.filter(materia__nivel__periodo=periodo).distinct()
                if not persona.usuario.is_staff:
                    solicitudes = solicitudes.filter(status=True)

                if txt_filter:
                    search = txt_filter.strip()
                    solicitudes = solicitudes.filter(Q(materia__asignatura__nombre__icontains=search))

                if type_request > 0:
                    solicitudes = solicitudes.filter(Q(tiposolicitud=type_request) | Q(tipoincoveniente_id=type_request))

                if type_motive > 0:
                    solicitudes = solicitudes.filter(Q(tipomotivo=type_motive) | Q(motivoincoveniente_id=type_motive))

                if state > 0:
                    solicitudes = solicitudes.filter(estado=state)

                tCount = solicitudes.count()
                if offset == 0:
                    rows = solicitudes[offset:limit]
                else:
                    rows = solicitudes[offset:offset + limit]
                aaData = []
                for row in rows:
                    materia = f"<b>Materia:</b> {row.materia.nombre_horario()}"
                    if row.tipo_profesor():
                        materia += f"<br> <b>Tipo Profesor:</b> <span class='label label-default'>{row.tipo_profesor().nombre}</span>"
                    if row.aula:
                        materia += f"<br> <b>Aula:</b> {row.aula.__str__()}"
                    if row.mi_clase():
                        materia += f"<br> <b>Tipo Horario:</b> <span class='label label-info'>{row.mi_clase().get_tipohorario_display()}</span>"
                    motivo = ''

                    aaData.append([materia,
                                   row.turno.__str__(),
                                   row.fechadiferido.strftime("%d-%m-%Y") if row.fechadiferido else "-",
                                   row.fecha.strftime("%d-%m-%Y") if row.fecha else "-",
                                   row.tipoincoveniente.__str__() if row.tipoincoveniente else row.get_tiposolicitud_display() if row.tiposolicitud else '-',
                                   row.motivoincoveniente.__str__() if row.motivoincoveniente else row.get_tipomotivo_display() if row.tipomotivo else '-',
                                   row.documento.url if row.documento and row.documento.url else None,
                                   row.get_estado_display(),
                                   {"id": row.id,
                                    "text": row.text_verbose(),
                                    "estado": row.estado,
                                    "aperturada": 1 if row.aperturada else 0,
                                    "existe_toma_asistencia": 1 if row.existe_toma_asistencia() else 0,
                                    "esta_aprobada": 1 if row.esta_aprobada() else 0,
                                    "tiposolicitud": row.tipoincoveniente.id if row.tipoincoveniente else row.tiposolicitud if row.tiposolicitud else 0,
                                    "reemplazo": 1 if row.reemplazo else 0,
                                    "profesor_principal_id": row.materia.profesor_principal().persona.id if row.materia and row.materia.profesor_principal() else 0,
                                    "en_fecha": 1 if row.en_fecha() else 0,
                                    "coordinacion_id": row.materia.coordinacion().id if row.materia.coordinacion() else None,
                                    "debe_subir_enlace": 1 if row.debe_subir_enlace() else 0,
                                    "tiene_enlace_diferido": 1 if row.tiene_enlace_diferido() else 0,
                                    "codigo_enlace_diferido": row.codigo_enlace_diferido() if row.codigo_enlace_diferido() else 0,
                                    "tiene_clase_abierta": 1 if row.tiene_clase_abierta() else 0,
                                    "clase_lecciongrupo": row.clase_lecciongrupo().id if row.clase_lecciongrupo() else None,
                                    "clase_leccion": encrypt(row.clase_leccion().id) if row.clase_leccion() else None,
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'deleteRequest':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Parametro no encontrado")
                if not SolicitudAperturaClase.objects.values("id").filter(pk=request.POST['id']).exists():
                    raise NameError(u"Solicitud no encontrada")
                delete = solicitud = SolicitudAperturaClase.objects.get(pk=request.POST['id'])
                solicitud.delete()
                log(u'Elimino solicitud de apertura de clase: %s' % delete, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Solicitud eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. %s" % ex.__str__()})

        elif action == 'addVideoVirtual':
            try:
                from Moodle_Funciones import CrearClaseVirtualClaseMoodleDiferido
                if not 'ids' in request.POST:
                    raise NameError(u"Parametro de solicitud no encontrado")
                if not 'link_1' in request.POST:
                    raise NameError(u"Parametro de enlace 1  de la clase no encontrado")
                if not 'link_2' in request.POST:
                    raise NameError(u"Parametro de enlace 2 de la clase no encontrado")
                if not 'link_3' in request.POST:
                    raise NameError(u"Parametro de enlace 3 de la clase no encontrado")
                if not request.POST['link_1']:
                    raise NameError(u"Enlace de la grabación 1 es obligatorio")
                ids = int(request.POST['ids'])
                link_1 = request.POST['link_1']
                link_2 = request.POST['link_2']
                link_3 = request.POST['link_3']
                if not SolicitudAperturaClase.objects.values("id").filter(pk=ids).exists():
                    raise NameError(u"Solicitud no encontrada")
                solicitud = SolicitudAperturaClase.objects.get(pk=ids)
                dia = int(solicitud.fecha.isocalendar()[2])
                semana = int(solicitud.fecha.isocalendar()[1])
                fechastr = str(solicitud.fecha)
                clase = solicitud.mi_clase()
                if not clase:
                    raise NameError(u"Clase no encontrada")
                CrearClaseVirtualClaseMoodleDiferido(clase.id, persona.id, link_1, link_2, link_3, dia, semana, fechastr)
                return JsonResponse({"result": "ok", "mensaje": u"Video guardado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el video. %s" % ex.__str__()})

        elif action == 'addVideoVirtual':
            try:
                from Moodle_Funciones import CrearClaseAsincronicaMoodleDiferido, CrearClaseSincronicaMoodleDiferido, CrearClaseVirtualClaseMoodleDiferido
                if not 'ids' in request.POST:
                    raise NameError(u"Parametro de clase no encontrado")
                if not 'link_1' in request.POST:
                    raise NameError(u"Parametro de enlace 1  de la clase no encontrado")
                if not 'link_2' in request.POST:
                    raise NameError(u"Parametro de enlace 2 de la clase no encontrado")
                if not 'link_3' in request.POST:
                    raise NameError(u"Parametro de enlace 3 de la clase no encontrado")
                if not 'dia' in request.POST:
                    raise NameError(u"Parametro de día de la clase no encontrado")
                if not request.POST['link_1']:
                    raise NameError(u"Enlace de la grabación 1 es obligatorio")
                ids = int(request.POST['ids'])
                link_1 = request.POST['link_1']
                link_2 = request.POST['link_2']
                link_3 = request.POST['link_3']
                if not SolicitudAperturaClase.objects.values("id").filter(pk=ids).exists():
                    raise NameError(u"Solicitud no encontrada")
                solicitud = SolicitudAperturaClase.objects.get(pk=ids)
                dia = int(solicitud.fecha.isocalendar()[2])
                semana = int(solicitud.fecha.isocalendar()[1])
                fechastr = str(solicitud.fecha)
                clase = solicitud.mi_clase()
                if not clase:
                    raise NameError(u"Clase no encontrada")
                materia = clase.materia
                coordinacion = materia.coordinacion()
                modalidad = materia.asignaturamalla.malla.modalidad
                if coordinacion is None:
                    raise NameError(u"Clase no tiene coordinación configurada")
                if not coordinacion.id in [1, 2, 3, 4, 5, 9, 7, 10, 12]:
                    raise NameError(u"Coordinación: %s no esta configurada en horario" % coordinacion.__str__())
                if coordinacion.id in [1, 2, 3, 4, 5, 12]:
                    if clase.tipohorario == 1:
                        raise NameError(u"Clase de tipo presencial no se sube video")
                    elif clase.tipohorario in [2, 7, 8, 9]:
                        if modalidad:
                            if modalidad.id in [1, 2]:
                                if clase.tipohorario in [2, 8]:
                                    CrearClaseVirtualClaseMoodleDiferido(clase.id, persona, link_1, link_2, link_3, dia, semana, fechastr)
                            elif modalidad.id in [3]:
                                if clase.tipohorario in [2, 8]:
                                    CrearClaseSincronicaMoodleDiferido(clase.id, persona, link_1, link_2, link_3, dia, semana, fechastr)
                                elif clase.tipohorario in [7, 9]:
                                    CrearClaseAsincronicaMoodleDiferido(clase.id, persona, link_1, link_2, link_3, dia, semana, fechastr)
                elif coordinacion.id in [9]:
                    CrearClaseVirtualClaseMoodleDiferido(clase.id, persona, link_1, link_2, link_3, dia, semana, fechastr)
                elif coordinacion.id in [7, 10]:
                    CrearClaseVirtualClaseMoodleDiferido(clase.id, persona, link_1, link_2, link_3, dia, semana, fechastr)
                return JsonResponse({"result": "ok", "mensaje": u"Video guardado correctamente"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'listMateriaEnFecha':
            try:
                materias = []
                ids = []
                fi = convertir_fecha(request.POST['fi'])
                ff = convertir_fecha(request.POST['ff'])
                if fi > ff:
                    raise NameError("La Fecha de Inicio debe ser menor a la Fecha de Fin")
                fechas = extraer_dias(fi, ff)
                profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17]).distinct().order_by('desde', 'materia__asignatura__nombre')
                for profesormateria in profesormaterias:
                    for fecha in fechas:
                        if profesormateria.esta_dia_con_horario(fecha):
                            data = profesormateria.asistencia_docente(fecha, fecha, periodo)
                            if data['total_asistencias_dias_tutoria'] > 0 or data['total_asistencias_dias_feriados'] > 0 or data['total_asistencias_dias_suspension'] > 0 or data['total_asistencias_no_registradas'] > 0:
                                ids.append(profesormateria.materia.id)
                if periodo.ocultarmateria:
                    materias = []
                else:
                    for materia in Materia.objects.filter(pk__in=ids).distinct().order_by('asignatura__nombre'):
                        materias.append([materia.id, materia.__str__()])
                return JsonResponse({'result': 'ok', 'lista': materias})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'loadMotivo':
            try:
                id = int(request.POST['id'])
                motivos = MotivoTipoInconvenienteClaseDiferido.objects.filter(pk=id)
                aData = serializers.serialize("json", motivos, fields=('nombre', 'activo', 'es_otro', 'obligar_archivo', 'aprobar_direccion'))
                return JsonResponse({'result': 'ok', 'aData': aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'saveAddRequest':
            try:
                documentFile = None
                if 'documento' in request.FILES:
                    documentFile = request.FILES['documento']
                    if documentFile.size > 20480000:
                        raise NameError(u"Tamaño de archivo Maximo permitido es de 5Mb")
                    documentFiled = documentFile._name
                    ext = documentFiled[documentFiled.rfind("."):]
                    if not ext in ['.pdf']:
                        raise NameError(u"Solo archivo con extensión. pdf")
                    documentFile._name = generar_nombre("aperturaclase_", documentFile._name)
                f = SolicitudAperturaClaseForm(request.POST, request.FILES)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                materia = f.cleaned_data['materia']
                incoveniente = f.cleaned_data['tipoincoveniente']
                motivo = f.cleaned_data['tipomotivo']
                fechainicioinasistencia = f.cleaned_data['fechainicioinasistencia']
                fechafininasistencia = f.cleaned_data['fechafininasistencia']
                # fechadiferido = f.cleaned_data['fechadiferido']
                fechasrango = []
                if fechainicioinasistencia == fechafininasistencia:
                    fechasrango.append(fechainicioinasistencia)
                else:
                    for dia in daterange(fechainicioinasistencia, (fechafininasistencia + timedelta(days=1))):
                        if not DiasNoLaborable.objects.filter(periodo=periodo, fecha=dia).exists():
                            fechasrango.append(dia)
                cantidad_dias_aperturar_clase = 1
                # CANTIDAD_DIAS_APERTURAR_CLASE = variable_valor('CANTIDAD_DIAS_APERTURAR_CLASE')
                if ePeriodoAcademia.puede_solicitar_clase_diferido_pro and ePeriodoAcademia.proceso_solicitud_clase_diferido_pro.num_dias > 0:
                    cantidad_dias_aperturar_clase = ePeriodoAcademia.proceso_solicitud_clase_diferido_pro.num_dias
                if (fechainicioinasistencia + timedelta(days=cantidad_dias_aperturar_clase)) < datetime.now().date():
                    raise NameError(u" Hasta las %s días puede solicitar apertura de clase." % cantidad_dias_aperturar_clase)
                if fechainicioinasistencia > datetime.now().date():
                    raise NameError(u"La fecha no puede ser mayor que hoy.")
                if fechafininasistencia >= datetime.now().date():
                    raise NameError(u"La fecha no puede ser mayor que hoy.")
                # if fechadiferido < datetime.now().date():
                #     raise NameError(u"La fecha diferido no puede ser menor o igual que hoy.")
                banSave = False
                solicitudes = []
                for fecha in fechasrango:
                    dia = fecha.isoweekday()
                    ban = 0
                    tiposprofesor = TipoProfesor.objects.filter(clase__dia=dia, clase__materia=materia, clase__activo=True, clase__profesor=profesor).values_list('id').distinct()

                    for tipoprofesor in tiposprofesor:
                        clases = Clase.objects.filter(dia=dia, materia=materia, activo=True, profesor=profesor, tipoprofesor_id=tipoprofesor).order_by("-turno_id")
                        for clase in clases:
                            ban = 0
                            # estado = 1
                            if materia.clase_set.filter(inicio__lte=fecha, fin__gte=fecha, dia=dia, activo=True, turno=clase.turno).exists():
                                estado = 1
                                reemplazo = False
                                if materia.es_profesormateria_reemplazo_pm(profesor):
                                    reemplazo = True
                                    lecciones = Leccion.objects.values("id").filter(status=True, clase__activo=True, fecha=fecha, clase__materia=materia, clase__turno=clase.turno, clase__materia__profesormateria__profesor=materia.profesor_principal(), clase__tipoprofesor_id=tipoprofesor)
                                    if lecciones.values("id").exists():
                                        if clase.grupoprofesor:
                                            if lecciones.values("id").filter(clase__grupoprofesor=clase.grupoprofesor).exists():
                                                ban = 1
                                        else:
                                            ban = 1
                                else:
                                    lecciones = Leccion.objects.filter(status=True, clase__activo=True, fecha=fecha, clase__materia=materia, clase__turno=clase.turno, clase__materia__profesormateria__profesor=materia.profesor_principal(), clase__tipoprofesor_id=tipoprofesor)
                                    if lecciones.values("id").exists():
                                        if clase.grupoprofesor:
                                            if lecciones.values("id").filter(clase__grupoprofesor=clase.grupoprofesor).exists():
                                                ban = 1
                                        else:
                                            ban = 1
                                if SolicitudAperturaClase.objects.values("id").filter(profesor=profesor, materia=materia, fecha=fecha, turno=clase.turno).exists():
                                    ban = 1
                                # if ClaseAsincronica.objects.values("id").filter(clase__materia=clase.materia, clase__tipoprofesor=clase.tipoprofesor, fechaforo=fecha, status=True).exists():
                                #     ban = 1

                                if ban == 0:

                                    # if materia.asignaturamalla.malla.carrera.mi_coordinacion2() == 9:
                                    #     estado = 2
                                    if ePeriodoAcademia.puede_solicitar_clase_diferido_pro and not motivo.aprobar_direccion:
                                        estado = 2

                                    solicitud = SolicitudAperturaClase(profesor=profesor,
                                                                       materia=materia,
                                                                       fecha=fecha,
                                                                       tiposolicitud=None,
                                                                       tipoincoveniente=incoveniente,
                                                                       tipomotivo=None,
                                                                       motivoincoveniente=motivo,
                                                                       motivo='',
                                                                       aula=f.cleaned_data['aula'],
                                                                       turno=clase.turno,
                                                                       reemplazo=reemplazo,
                                                                       estado=estado,
                                                                       especifique=f.cleaned_data['especifique'] if f.cleaned_data['especifique'] else None,
                                                                       fechadiferido=None,
                                                                       documento=documentFile)
                                    solicitud.save(request)
                                    log(u'Adiciono solicitud apertura de clase: %s' % solicitud, request, "add")
                                    banSave = True
                                    solicitudes.append(solicitud)

                if not banSave:
                    raise NameError(u"No se generero ninguna solicitud, porque en la fecha si tiene registrado asistencias o solicitudes.")
                if ePeriodoAcademia.puede_solicitar_clase_diferido_pro and motivo.aprobar_direccion:
                    enviar_notificacion_solicitud_registro_asistencia_pro(profesor, solicitudes)
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente la solicitud"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al guardar la solicitud. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormRequest':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    if typeForm == 'new':
                        f = SolicitudAperturaClaseForm(initial={'fechainasistencia': datetime.now().date()})
                        f.set_tipo(periodo)
                        f.set_materia(profesor, periodo)
                        data['ePeriodo'] = periodo
                        data['form'] = f
                        data['frmName'] = "frmAddRequest"
                    else:
                        pass
                    template = get_template("pro_aperturaclase/addsolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Registro de Asistencias - Por inconvenientes y diferidos de clases'
            data['profesor'] = profesor
            # solicitudes = profesor.solicitudaperturaclase_set.filter(materia__nivel__periodo=periodo).distinct()
            data['estados'] = ESTADOS_PREPROYECTO
            data['ePeriodoAcademia'] = ePeriodoAcademia
            data['tipos_incovenientes'] = ePeriodoAcademia.tipos_incovenientes_por_diferido()
            # data['tipos_motivo'] = TIPO_MOTIVO
            return render(request, "pro_aperturaclase/view.html", data)


def extraer_dias(fecha_inicio, fecha_fin):
    listafecha = []
    while fecha_inicio <= fecha_fin:
        listafecha.append(fecha_inicio)
        fecha_inicio += timedelta(days=1)
    return listafecha


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)
