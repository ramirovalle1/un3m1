# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.models import CapTurnoIpec, CapInstructorIpec
from sga.commonviews import adduserdata
from sga.models import Profesor, Turno
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    instructor = []
    if not CapInstructorIpec.objects.values("id").filter(instructor=persona):
        return HttpResponseRedirect("/?info=Solo los instructores pueden ingresar al modulo.")

    if CapInstructorIpec.objects.filter(status=True, instructor=persona, instructorprincipal=True, activo=True).exists():
        instructor = CapInstructorIpec.objects.filter(status=True, instructor=persona, instructorprincipal=True, activo=True)[0]
    if not instructor:
        return HttpResponseRedirect("/?info=No tiene horarios activos.")
    periodo =''
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'pdf_horarios':
            data = {}
            data['periodo'] = periodo
            if not periodo.visible:
                return HttpResponseRedirect("/?info=No tiene permiso para imprimir en el periodo seleccionado.")
            data['profesor'] = profesor = Profesor.objects.filter().distinct().get(pk=request.POST['profesor'])
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],[6, 'Sabado'], [7, 'Domingo']]
            turnosyclases = profesor.extrae_turnos_y_clases_docente(periodo)
            turnoactividades = Turno.objects.filter(status=True, claseactividad__detalledistributivo__distributivo__periodo=periodo, claseactividad__detalledistributivo__distributivo__profesor=profesor).distinct().order_by('comienza')
            data['turnos'] = turnosyclases[1] | turnoactividades
            data['puede_ver_horario'] = request.user.has_perm('sga.puede_visible_periodo') or (periodo.visible == True and periodo.visiblehorario == True)
            data['aprobado'] = profesor.claseactividadestado_set.filter(status=True, periodo=periodo, estadosolicitud=2).exists()
            return conviert_html_to_pdf(
                'docentes/horario_pfd.html',
                {
                    'pagesize': 'A4',
                    'data': data,
                }
            )

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        try:
            data['title'] = u'Horario de instructores de IPEC'
            data['capeventoperiodo'] = None
            data['eventoperiodoid'] = None
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
            data['turnos'] = CapTurnoIpec.objects.filter(status=True)
            data['instructor'] = instructor
            data['disponible'] = instructor.capclaseipec_set.filter(status=True) if instructor else False
            return render(request, "ins_horariocapacitacionipec/view.html", data)
        except Exception as ex:
            pass
