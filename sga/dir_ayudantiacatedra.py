import random

import xlwt
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from datetime import datetime, timedelta
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import PeriodoCatedraForm, InscripcionCatedraEstadoForm, InscripcionCatedraArchivoForm, \
    SupervisorAyudantiaCatedraForm, ActividadInscripcionCatedraForm, ActividadAyudantiaCatedraForm, \
    InformeAyudanteCatedraEstadoForm, InscripcionCatedraAprobarForm, ArchivoGeneralCatedraForm, \
    SolicitudProfesorCatedraForm
from sga.funciones import MiPaginador, log, generar_nombre, puede_realizar_accion, puede_realizar_accion_afirmativo, \
    puede_realizar_acciones_afirmativo, null_to_numeric
from sga.models import PeriodoCatedra, Carrera, InscripcionCatedra, ActividadInscripcionCatedra, miinstitucion, \
    CUENTAS_CORREOS, ActividadAyudantiaCatedra, InformeAyudanteCatedra, AprobacionInformeAyudanteCatedra, \
    PracticasPreprofesionalesInscripcion, DetalleEvidenciasPracticasPro, ArchivoGeneralCatedra, \
    SolicitudProfesorCatedra, DIAS_CHOICES
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt

unicode =str
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
    eCarreraTercerNivel = persona.mis_carreras_tercer_nivel().values_list('id', flat=True)
    es_director_carr = eCarreraTercerNivel.exists()
    #persona.mis_carreras_tercer_nivel().filter(coordinacion__id__in=[3, 4, 5, 6])
    if not es_director_carr:
        return HttpResponseRedirect("/?info=El Módulo está disponible para Directores de Carrera")

    permiter_director = eCarreraTercerNivel.filter(coordinacion__id__in=[3, 4, 5, 6]).exists()

    if not permiter_director:
        return HttpResponseRedirect("/?info=El Módulo está disponible para directores que permiten ayudantías de cátedra")

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'loadDataTableSolicitudesProfesorCatedra':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                tCount = 0
                periodocatedra_id = int(encrypt(request.POST.get('periodocatedra_id', encrypt(0))))
                solicitudes = SolicitudProfesorCatedra.objects.filter(status=True)
                if periodocatedra_id > 0:
                    solicitudes = solicitudes.filter(periodocatedra_id=periodocatedra_id)

                if txt_filter:
                    search = txt_filter.strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        solicitudes = solicitudes.filter(
                            Q(descripcion__icontains=search) |
                            Q(profesor__persona__cedula__icontains=search) |
                            Q(profesor__persona__pasaporte__icontains=search) |
                            Q(profesor__persona__ruc__icontains=search) |
                            Q(profesor__persona__nombres__icontains=search) |
                            Q(profesor__persona__apellido1__icontains=search) |
                            Q(profesor__persona__apellido2__icontains=search)
                        )
                    else:
                        solicitudes = solicitudes.filter(
                            ((Q(profesor__persona__nombres__icontains=ss[0]) & Q(profesor__persona__nombres__icontains=ss[1])) |
                             (Q(profesor__persona__apellido1__icontains=ss[0]) & Q(profesor__persona__apellido2__icontains=ss[1])))
                        )
                tCount = solicitudes.count()
                if offset == 0:
                    rows = solicitudes[offset:limit]
                else:
                    rows = solicitudes[offset:offset + limit]
                aaData = []
                for row in rows:
                    materias = [{
                        'id': detallesoli.materia.id,
                        'name': u'%s - %s - %s' % (detallesoli.materia.asignaturamalla.asignatura.nombre, detallesoli.materia.paralelomateria.__str__(), detallesoli.materia.nivel.paralelo),
                        'number_students': detallesoli.numero_estudiantes,
                        'horarios': [{
                            'id': horario.id,
                            'dia': horario.get_dia_display(),
                            'horainicio': horario.horainicio.strftime("%H:%M %p"),
                            'horafin': horario.horafin.strftime("%H:%M %p"),
                        }for horario in detallesoli.detallehorariosolicitudprofesorcatedra_set.filter(status=True)]
                    }for detallesoli in row.detallesolicitudprofesorcatedra_set.filter(status=True)]
                    aaData.append([{
                                    'numero': row.numero,
                                    'periodocatedra': row.periodocatedra.__str__(),
                                    'periodo': row.periodocatedra.periodolectivo.__str__(),
                                    },
                                   {"id": row.id,
                                    "name": row.__str__(),
                                    "docente": {
                                        'name': row.profesor.__str__(),
                                        'foto': row.profesor.persona.get_foto(),
                                    },
                                    "carrera": row.carrera.__str__(),
                                    },
                                   {
                                    'name': row.profesor.__str__(),
                                    'foto': row.profesor.persona.get_foto(),
                                    'email': row.profesor.persona.email,
                                    'emailinst': row.profesor.persona.emailinst,
                                    'cedula': row.profesor.persona.cedula,
                                    'direccion': row.profesor.persona.direccion,
                                    'telefono': row.profesor.persona.telefono,
                                   },
                                    materias,
                                   {
                                       'estado': row.estado,
                                       'estado_display': row.get_estado_display()
                                   },
                                   {"id": row.id,
                                    "id_encr": encrypt(row.id),
                                    "name": row.__str__(),
                                    "numero": row.numero,
                                    'estado': row.estado,
                                    'puede_gestionar_solicitud': row.periodocatedra.puede_gestionar_solicitudes_directores(),
                                    }
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'CambiarEstadoSolicitudProfesorCatedra':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                estado = request.POST['estado']
                observacion = request.POST['observacion']
                eSolicitudProfesorCatedra = SolicitudProfesorCatedra.objects.filter(pk=id, status=True).first()
                if eSolicitudProfesorCatedra is None:
                    raise NameError('No se encontro solicitud')
                eSolicitudProfesorCatedra.estado = estado
                eSolicitudProfesorCatedra.observacion = observacion
                eSolicitudProfesorCatedra.save(request)
                log(u'Actualizó estado de ayudante de catedara: %s al siguiente estado %s --> %s' % (eSolicitudProfesorCatedra, eSolicitudProfesorCatedra.get_estado_display(), eSolicitudProfesorCatedra.observacion), request, "edit")
                # eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria,
                #                                                    observacion=observacion,
                #                                                    estado=eSolicitudFeria.estado)
                # eSolicitudFeriaHistorial.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Se cambio correctamente el estado de la solicitud"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Solicitudes para ayudantías de cátedra'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormSolicitudProfesorCatedra':
                try:
                    data['title'] = u'Adicionar informe ayudante'
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(
                        request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    form = SolicitudProfesorCatedraForm()
                    eSolicitudPofesorCatedra = None
                    id = 0
                    # idscarrdocente = profesor.mis_materias(periodo).values_list('materia__asignaturamalla__malla__carrera_id', flat=True).distinct()
                    # form.fields['carrera'].queryset = form.fields['carrera'].queryset.filter(pk__in=idscarrdocente)
                    eMaterias = []
                    if typeForm in ['edit', 'view']:
                        id = int(encrypt(request.GET['id'])) if 'id' in request.GET and encrypt(
                            request.GET['id']) and int(encrypt(request.GET['id'])) != 0 else None
                        eSolicitudPofesorCatedra = SolicitudProfesorCatedra.objects.filter(pk=id, status=True).first()
                        if eSolicitudPofesorCatedra is None:
                            raise NameError(u"No solicitud con el parametro id")
                        form.initial = model_to_dict(eSolicitudPofesorCatedra)
                        if typeForm == 'edit':
                            form.editar()
                        if typeForm == 'view':
                            form.view()
                        for eMateria in eSolicitudPofesorCatedra.detalle_materias():
                            eMateriaHorariodict = [
                                {
                                    'idh': horario.id,
                                    'dia': horario.dia,
                                    'horainicio': horario.horainicio.strftime("%H:%M"),
                                    'horafin': horario.horafin.strftime("%H:%M"),
                                } for horario in eMateria.detalle_horario()
                            ]
                            eMateriadict = {
                                'id': eMateria.materia_id,
                                'name': eMateria.__str__(),
                                'text': u'%s - %s' % (eMateria.materia.asignaturamalla.asignatura.nombre,
                                                      eMateria.materia.paralelomateria.__str__()),
                                'paralelo': eMateria.materia.paralelomateria.__str__(),
                                'horarios': eMateriaHorariodict,
                                'detalle_id': eMateria.id,
                                'numero_estudiantes': eMateria.numero_estudiantes,
                            }
                            eMaterias.append(eMateriadict)
                    else:
                        pass
                    data['form'] = form
                    data['frmName'] = "frmSolicitudProfesorCatedra"
                    data['typeForm'] = typeForm
                    data['id'] = encrypt(id)
                    data['eSolicitudPofesorCatedra'] = eSolicitudPofesorCatedra
                    template = get_template("dir_ayudantiacatedra/frmSolicitudProfesorCatedra.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"result": "ok", 'html': json_content, 'eMaterias': eMaterias})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            data['dias'] = DIAS_CHOICES
            ePeriodosDirectorCarrera = persona.coordinadorcarrera_set.filter(status=True, tipo=3).values_list('periodo_id', flat=True).distinct()
            data['ePeriodosCatedra'] = ePeriodosCatedra = PeriodoCatedra.objects.filter(status=True, periodolectivo_id__in=ePeriodosDirectorCarrera)
            ePeriodoCatedra = ePeriodosCatedra.order_by('-fechadesde').first()
            data['periodocatedra_id'] = ePeriodoCatedra.id if ePeriodoCatedra is not None else 0
            return render(request, "dir_ayudantiacatedra/view.html", data)