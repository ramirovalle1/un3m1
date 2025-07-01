# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import CLASES_APERTURA_ANTES
from sga.commonviews import adduserdata
from sga.funciones import log
from sga.models import Sesion, Clase, SesionZoom, MateriaAsignada, DesactivarSesionZoom,DetalleSesionZoom
from sga.commonviews import get_client_ip

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
    # if datetime(2021, 5, 28, 0, 0, 0).date() == datetime.now().date():
    if confirmar_automatricula_admision and periodo.limite_agregacion < datetime.now().date():
        cordinacionid = inscripcion.carrera.coordinacion_carrera().id
        if cordinacionid in [9]:
            return HttpResponseRedirect("/?info=Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addcliczoom':
            try:
                if request.POST['clase']:
                    clase = Clase.objects.get(pk=int(request.POST['clase']))
                    matricula = inscripcion.mi_matricula_periodo(periodo.id)
                    materiaasignada= MateriaAsignada.objects.get(matricula=matricula,materia=clase.materia,status=True)
                    diaactual = datetime.now().date().isocalendar()[2]
                    horaactual= datetime.now().time()
                    clases = Clase.objects.filter(materia=materiaasignada.materia, dia=diaactual,status=True)
                    #EXCLUIR INGLES
                    if clase.materia.coordinacion_materia().pk == 6:
                        return JsonResponse({"result": "ok"})

                    for cla in clases:
                        if not SesionZoom.objects.filter(materiaasignada=materiaasignada,clase=cla,status=True,fecha=datetime.now().date()).exists():
                            zoom = SesionZoom(
                                materiaasignada = materiaasignada,
                                modulo = 1,
                                fecha = datetime.now().date(),
                                hora = datetime.now().time(),
                                clase = cla,
                                activo=True,
                                # ip_public=client_address
                            )
                            zoom.save(request)
                            if cla.turno.termina >= horaactual:
                                zoom.activo = True
                            else:
                                zoom.activo = False
                                zoom.save(request)
                                obser = DesactivarSesionZoom(sesion=zoom,
                                                             observacion="NO ASISTIÓ")
                                obser.save()
                        else:
                            zoom = SesionZoom.objects.get(materiaasignada=materiaasignada,clase=cla,status=True,fecha=datetime.now().date())
                            zoom.horaultima = datetime.now().time()
                            if cla.turno.termina >= horaactual:
                                zoom.activo = True
                        zoom.save(request)
                        client_address = get_client_ip(request)
                        browser = request.POST['navegador']
                        ops = request.POST['os']
                        screensize = request.POST['screensize']
                        detalle=DetalleSesionZoom(
                            sesion=zoom,
                            ip_public=client_address,
                            browser=browser,
                            screen_size=screensize,
                            ops=ops,
                            fecha=datetime.now().date(),
                            hora=datetime.now().time()
                        )
                        detalle.save()
                        log(u'Adiciono asistencia: %s' % cla, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Horario de estudiante'
        hoy = datetime.now().date()
        if not request.session['periodo']:
            return HttpResponseRedirect("/?info=No tiene periodo asignado.")
        data['matricula'] = matricula = inscripcion.mi_matricula_periodo(periodo.id)
        if not matricula:
            return HttpResponseRedirect("/?info=Ud. no se encuentra matriculado")
        data['numerosemanaactual'] = datetime.today().isocalendar()[1]
        data['materias'] = matricula.materiaasignada_set.all()
        data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
        data['misclases'] = clases = Clase.objects.filter(fin__gte=hoy ,activo=True, materia__materiaasignada__matricula_id=matricula.id, materia__materiaasignada__retiramateria=False).distinct().order_by('inicio')
        data['misclasespasadas'] = clases2 = Clase.objects.filter(fin__lt=hoy,activo=True, materia__materiaasignada__matricula_id=matricula.id, materia__materiaasignada__retiramateria=False).distinct().order_by('inicio')
        data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases.values_list("id").distinct() | clases2.values_list("id").distinct()).distinct()
        data['idperiodo'] = periodo.id
        data['fechaactual'] = hoy
        data['diaactual'] = hoy.isocalendar()[2]
        return render(request, "alu_horarios/view_old.html", data)

