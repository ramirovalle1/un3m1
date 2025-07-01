# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.models import CapInstructorIpec, CapPeriodoIpec, CapCabeceraAsistenciaIpec, CapClaseIpec, \
    CapDetalleAsistenciaIpec
from sga.commonviews import adduserdata
from sga.funciones import log

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if not CapInstructorIpec.objects.values("id").filter(instructor=persona):
        return HttpResponseRedirect("/?info=Solo los instructores pueden ingresar al modulo.")
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'nuevaasistencia':
                try:
                    asis = CapCabeceraAsistenciaIpec.objects.filter(fecha=datetime.now().date(), clase_id=int(request.POST["id"]), status=True)
                    clase = CapClaseIpec.objects.get(pk=int(request.POST['id']))
                    if not clase.capeventoperiodo.exiten_inscritos():
                        return JsonResponse({"result": "bad", "mensaje": u"No puede continuar, porque no existen inscritos."})
                    if not asis.exists():
                        asistencia = CapCabeceraAsistenciaIpec(clase=clase,
                                                               fecha=datetime.now().date(),
                                                               horaentrada=clase.turno.horainicio,
                                                               horasalida=clase.turno.horafin,
                                                               contenido="SIN CONTENIDO",
                                                               observaciones="SIN OBSERVACIONES")
                        asistencia.save(request)
                        log(u'Agrego Asistencia en Capacitacion IPEC: %s [%s]' % (asistencia, asistencia.id), request, "add")
                        for integrante in clase.capeventoperiodo.inscritos():
                            resultadovalores = CapDetalleAsistenciaIpec(inscrito=integrante, cabeceraasistencia=asistencia, asistio=False)
                            resultadovalores.save(request)
                    else:
                        asistencia = asis[0]
                    return JsonResponse({"result": "ok", 'id': asistencia.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addasistenciagrupal':
                try:
                    cadenaselect = request.POST['cadenaselect']
                    cadenanoselect = request.POST['cadenanoselect']
                    cadenadatos = cadenaselect.split(',')
                    cadenanodatos = cadenanoselect.split(',')
                    asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                    for cadena in cadenadatos:
                        if cadena:
                            if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=cadena, status=True).exists():
                                resultadovalores = asistencia.capdetalleasistenciaipec_set.get(inscrito_id=cadena, status=True)
                                resultadovalores.asistio = True
                                resultadovalores.save(request)
                            else:
                                resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=cadena, cabeceraasistencia=asistencia, asistio=True)
                                resultadovalores.save(request)
                    for cadenano in cadenanodatos:
                        if cadenano:
                            if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=cadenano, status=True).exists():
                                resultadovalores = asistencia.capdetalleasistenciaipec_set.get(inscrito_id=cadenano, status=True)
                                resultadovalores.asistio = False
                                resultadovalores.save(request)
                            else:
                                resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=cadenano,
                                                                            cabeceraasistencia=asistencia,
                                                                            asistio=False)
                                resultadovalores.save(request)
                    log(u'Edito Asistencia en Capacitacion IPEC: %s [%s]' % (asistencia, asistencia.id), request, "edit")
                    data = {"result": "ok", "results": [{"id": x.inscrito.id, "porcientoasist": x.inscrito.porciento_asistencia_ipec(), "porcientorequerido": x.inscrito.porciento_requerido_asistencia_ipec()} for x in asistencia.capdetalleasistenciaipec_set.filter(status=True)]}
                    return JsonResponse(data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addasistenciaindividual':
                try:
                    asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                    if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=int(request.POST['idi']), status=True).exists():
                        resultadovalores = asistencia.capdetalleasistenciaipec_set.get(inscrito_id=int(request.POST['idi']), status=True)
                        resultadovalores.asistio = True if request.POST['valor'] == "y" else False
                        resultadovalores.save(request)
                    else:
                        resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=int(request.POST['idi']), cabeceraasistencia=asistencia, asistio=True if request.POST['valor'] == "y" else False)
                        resultadovalores.save(request)
                    datos = {}
                    datos['id'] = resultadovalores.inscrito.id
                    datos['porcientoasist'] = resultadovalores.inscrito.porciento_asistencia_ipec()
                    datos['porcientorequerido'] = resultadovalores.inscrito.porciento_requerido_asistencia_ipec()
                    datos['result'] = 'ok'
                    log(u'Edito Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (asistencia, asistencia.id), request, "edit")
                    return JsonResponse(datos)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addsaistenciacontenido':
                try:
                    asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                    asistencia.contenido = request.POST["valor"]
                    asistencia.save(request)
                    log(u'Edito Contenido de Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (
                    asistencia, asistencia.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addasistenciaobservacion':
                try:
                    asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                    asistencia.observaciones = request.POST["valor"]
                    asistencia.save(request)
                    log(u'Edito Observacion de Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (asistencia, asistencia.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'delclase':
                try:
                    asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                    for asi in asistencia.capdetalleasistenciaipec_set.all():
                        log(u'Eliminó asistencia del estudiante %s del evento de Capacitacion IPEC: %s  del turno [%s]' % (asi.inscrito, asistencia.clase.capeventoperiodo, asistencia), request, "del")
                    asistencia.capdetalleasistenciaipec_set.all().delete()
                    asistencia.delete()
                    log(u'Eliminó Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (asistencia, asistencia.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Registros de asistencia a clase'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'delclase':
                try:
                    data['title'] = u'Eliminar clase'
                    data['clase'] = CapCabeceraAsistenciaIpec.objects.get(pk=request.GET['id'])
                    return render(request, "ins_clases/delclase.html", data)
                except Exception as ex:
                    pass

            if action == 'asistencia':
                try:
                    revisar=False
                    data['title'] = u'Asistencia'
                    data['cabeceraasistencia'] = asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.GET['id']))
                    data['clase']= asistencia.clase
                    data['listadoinscritos'] = asistencia.clase.capeventoperiodo.inscritos()
                    # if not asistencia.fecha == datetime.now().date():
                    #     revisar=True
                    data['revisar'] = revisar
                    return render(request, "ins_clases/asistencia.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Registro de asistencia de clases IPEC'
            hoy = datetime.now().date()
            idc = 0
            data['periodos'] = periodos = CapPeriodoIpec.objects.values_list('id', 'nombre', 'fechainicio', 'fechafin', flat=False).filter(status=True, capeventoperiodoipec__capinstructoripec__instructor=persona).order_by('-id').distinct()
            idp = periodos[0][0]
            if 'idp' in request.GET:
                idp = int(request.GET['idp'])
            data['periodoselect'] = idp
            cursos = CapInstructorIpec.objects.filter(status=True, instructorprincipal=True, instructor=persona, capeventoperiodo__periodo__id=idp)
            clases = CapCabeceraAsistenciaIpec.objects.filter(clase__instructor__id__in=cursos.values_list('id', flat=True)).order_by('-fecha')
            if 'id' in request.GET:
                idc = int(request.GET['id'])
                clases = clases.filter(clase__capeventoperiodo__id=idc)
            paging = Paginator(clases, 30)
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
            data['page'] = page
            data['clases'] = page.object_list
            data['idc'] = idc
            data['cursos'] = cursos
            return render(request, "ins_clases/view.html", data)
