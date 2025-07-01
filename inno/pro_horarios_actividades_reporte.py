# -*- coding: latin-1 -*-
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction, connection, connections
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from mobi.decorators import detect_mobile

from decorators import secure_module, last_access
from sagest.models import LogMarcada
from sga.commonviews import adduserdata
from sga.funciones import convertir_fecha_invertida
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Periodo, Profesor, Materia


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
@detect_mobile
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=No puede abrir los perfiles de profesores el modulo.")
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'horarioactividadespdf':
            try:
                data['title'] = u'Horarios de las Actividades del Profesor'
                data['profesor'] = profesor = Profesor.objects.filter(id=int(request.POST['idprofesor']))[0]
                data['periodo'] = periodo = Periodo.objects.filter(id=int(request.POST['idperiodo']))[0]
                data['materias'] = Materia.objects.filter(profesormateria__profesor=profesor, profesormateria__principal=True, nivel__periodo=periodo).distinct().order_by('inicio')
                data['distributivo_horas'] = profesor.distributivohoraseval(periodo)

                cursor = connections['sga_select'].cursor()
                sql = "select tabladocente.carrera, tabladocente.nivel, tabladocente.paralelo, tabladocente.asignatura, tabladocente.horas , COALESCE(tablaasistencia.asistencia,0) as asistencia, " \
                " (select count(*) from sga_faltasmateriaperiodo fm1 where fm1.materia_id=tabladocente.materiaid) as faltas, (select count(*) from sga_solicitudaperturaclase sac where sac.status=true and sac.materia_id=tabladocente.materiaid and sac.profesor_id=tabladocente.profesorid and sac.estado=2)  as diferido " \
                " from (select pr.id as profesorid, pm.id as profesormateriaid, m.inicio, m.fin, m.id as materiaid, co.nombre as facultad, ca.nombre as carrera, nm.nombre as nivel, m.paralelo, (per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres) as docente,asi.nombre as asignatura, m.horas " \
                " from sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma,sga_carrera ca, sga_coordinacion_carrera cc, sga_coordinacion co, sga_nivelmalla nm, sga_profesor pr, sga_persona per, sga_asignatura asi " \
                " where m.id=pm.materia_id and n.id=m.nivel_id and am.id=m.asignaturamalla_id and ma.id=am.malla_id and ca.id=ma.carrera_id and cc.carrera_id=ca.id and co.id=cc.coordinacion_id and nm.id=am.nivelmalla_id and pr.id=pm.profesor_id and per.id=pr.persona_id " \
                " and asi.id=m.asignatura_id and n.periodo_id="+ str(periodo.id) +" AND per.id="+ str(profesor.persona.id) +" order by co.nombre, ca.nombre, nm.nombre, m.paralelo, docente) as tabladocente " \
                " left join (select mat1.id as materiaid, count(mat1.id) as asistencia from sga_leccion l1 , sga_clase c1 , sga_materia mat1, sga_nivel ni1 where l1.clase_id=c1.id and c1.materia_id=mat1.id and mat1.nivel_id=ni1.id " \
                " and l1.fecha>= '"+ request.POST['fechadesde'] +"' and l1.fecha<= '"+ request.POST['fechahasta'] +"' and ni1.periodo_id="+ str(periodo.id) +" " \
                " and l1.fecha not in (select dnl1.fecha from sga_diasnolaborable dnl1 where dnl1.periodo_id=11) GROUP by mat1.id) as tablaasistencia on tablaasistencia.materiaid=tabladocente.materiaid order by tabladocente.facultad , tabladocente.carrera, tabladocente.nivel, tabladocente.paralelo, tabladocente.docente"
                cursor.execute(sql)
                data['asistencias'] = cursor.fetchall()


                sql="select asi.nombre,count(*) from sga_planificacionmateria pm, sga_materia m, sga_nivel n, sga_profesormateria prm, sga_asignatura asi " \
                " where pm.status=true and m.id=pm.materia_id and m.status=true and pm.paraevaluacion=true and asi.id=m.asignatura_id and asi.status=true " \
                " and m.nivel_id=n.id and n.status=true and n.periodo_id="+ str(periodo.id) +" and prm.materia_id=m.id and prm.status=true and prm.profesor_id="+ str(profesor.id) +" GROUP by asi.id"
                cursor.execute(sql)
                data['tareas'] = cursor.fetchall()
                fechadesde = convertir_fecha_invertida(request.POST['fechadesde'])
                fechahasta = convertir_fecha_invertida(request.POST['fechahasta'])
                data['marcadas'] = LogMarcada.objects.values_list('time').filter(logdia__persona=profesor.persona, time__gte=fechadesde, time__lte=fechahasta, status=True).order_by('time').distinct()
                data['fechadesde'] = fechadesde
                data['fechahasta'] = fechahasta

                hoy = datetime.now().date()
                return conviert_html_to_pdf(
                    'pro_horarios_actividades_reporte/actividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Horarios de las Actividades del Profesor'
        data['periodos'] = periodos  = Periodo.objects.filter(status=True).order_by('-id')
        data['idperiodo'] = periodos[0].id
        data['fecha'] = str(datetime.now().date())
        return render(request, "pro_horarios_actividades_reporte/view.html", data)
