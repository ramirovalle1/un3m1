# -*- coding: UTF-8 -*-
from datetime import datetime, date
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.forms import CapClaseIpecForm, CapAsistenciaIpecForm
from sagest.models import CapEventoPeriodoIpec, CapInstructorIpec, CapClaseIpec, CapCabeceraAsistenciaIpec, CapDetalleAsistenciaIpec
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, variable_valor
from sga.models import DIAS_CHOICES
from django.db.models import Q


@login_required(redirect_field_name='ret',login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if not CapInstructorIpec.objects.filter(instructor=persona).exists():
        return HttpResponseRedirect('/?info=Usted no es instructor de Capacitación IPEC .')
    if request.method == 'POST':
        action = request.POST['action']

        # elif action == 'reporte_asistencia':
        #     try:
        #         persona_cargo_tercernivel=None
        #         revisadotercernivel=None
        #         aprobado1tercernivel=None
        #         aprobado2tercernivel=None
        #         data['idp'] = request.POST['id']
        #         data['evento'] = evento = CapEventoPeriodo.objects.get(status=True, id=int(request.POST['id']))
        #         data['fechas'] = fechas = evento.todas_fechas_asistencia()
        #         lista_fechas = CapCabeceraAsistencia.objects.values_list("fecha").filter(clase__capeventoperiodo=evento).distinct('fecha').order_by('fecha')
        #         contarcolumnas= CapCabeceraAsistencia.objects.filter(Q(clase__capeventoperiodo=evento)& Q(fecha__in=lista_fechas)).count()+6
        #         data['vertical_horizontal']= True if contarcolumnas>10 else False
        #         data['ubicacion_promedio'] = contarcolumnas-3
        #         data['elabora_persona'] = persona
        #         cargo=None
        #         if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
        #            cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
        #         data['persona_cargo'] = cargo
        #         data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
        #         if titulo:
        #             persona_cargo_tercernivel= persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id==4 else None
        #         data['revisado'] = revisado = evento.revisado.titulacion_principal_senescyt_registro()
        #         if revisado:
        #             revisadotercernivel= evento.revisado.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if revisado.titulo.nivel_id == 4 else None
        #         data['aprobado1'] = aprobado1 = evento.aprobado1.titulacion_principal_senescyt_registro()
        #         if aprobado1:
        #             aprobado1tercernivel = evento.aprobado1.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if aprobado1.titulo.nivel_id == 4 else None
        #         data['aprobado2'] = aprobado2 = evento.aprobado2.titulacion_principal_senescyt_registro()
        #         if aprobado2:
        #             aprobado2tercernivel= evento.aprobado2.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if aprobado2.titulo.nivel_id == 4 else None
        #         data['persona_cargo_tercernivel']=persona_cargo_tercernivel
        #         data['revisadotercernivel']=revisadotercernivel
        #         data['aprobado1tercernivel']=aprobado1tercernivel
        #         data['aprobado2tercernivel']=aprobado2tercernivel
        #         ultima_fecha=fechas.order_by('-fecha')[0].fecha
        #         if ultima_fecha.weekday() >= 0 and ultima_fecha.weekday() <= 3 or ultima_fecha.weekday() == 6:
        #             dias = timedelta(days=1)
        #         else:
        #             dias = timedelta(days=2)
        #         data['fecha_corte'] = ultima_fecha + dias
        #         return conviert_html_to_pdf('adm_capacitacioneventoperiodo/informe_asistencia_pdf.html',{'pagesize': 'A4', 'data': data})
        #     except Exception as ex:
        #         pass

        # elif action == 'reporte_certificado':
        #     try:
        #         persona_cargo_tercernivel=None
        #         cargo = None
        #         tamano=0
        #         cabecera = CapCabeceraSolicitud.objects.get(status=True, id=int(request.POST['id']))
        #         data['evento'] = evento = cabecera.capeventoperiodo
        #         evento.actualizar_folio()
        #         data['elabora_persona'] = persona
        #         if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
        #             cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
        #         data['persona_cargo'] = cargo
        #         data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
        #         if not titulo == '':
        #             persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
        #         data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
        #         data['inscrito'] = cabecera
        #         mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre","octubre", "noviembre", "diciembre"]
        #         data['fecha'] =  u"Milagro, %s de mes de %s del %s" % (datetime.now().day, str(mes[datetime.now().month - 1]),datetime.now().year)
        #         data['listado_contenido']= listado = evento.contenido.split("\n")
        #         if evento.objetivo.__len__()<290:
        #             if listado.__len__() < 21:
        #                 tamano = 120
        #             elif listado.__len__() < 35:
        #                 tamano = 100
        #             elif listado.__len__() < 41:
        #                 tamano = 70
        #
        #         data['controlar_bajada_logo']= tamano
        #         return conviert_html_to_pdf('adm_capacitacioneventoperiodo/certificado_individual_pdf.html',{'pagesize': 'A4', 'data': data})
        #     except Exception as ex:
        #         pass

        #INSTRUCTOR


        # HORARIOS

        if action == 'addclase':
            try:
                form = CapClaseIpecForm(request.POST)
                if form.is_valid():
                    periodo = CapEventoPeriodoIpec.objects.get(id=int(request.POST['cepid']))
                    if CapClaseIpec.objects.filter(capeventoperiodo_id=int(request.POST['cepid']),dia=form.cleaned_data['dia'], turno=form.cleaned_data['turno'],fechainicio=form.cleaned_data['fechainicio'],fechafin=form.cleaned_data['fechafin'], status=True).exists():
                        return JsonResponse({"result": "bad","mensaje": u"Hay una Clase que existe con las misma fechas y turno."})
                    if not form.cleaned_data['fechainicio'] >= periodo.fechainicio or not form.cleaned_data['fechafin'] <= periodo.fechafin:
                        return JsonResponse({"result": "bad","mensaje": u"Las fecha no puede ser mayor a las fecha del evento."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if form.cleaned_data['fechainicio'] == form.cleaned_data['fechafin']:
                        if not int(form.cleaned_data['dia']) == form.cleaned_data['fechainicio'].weekday()+1:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no concuerdan con el dia."})
                    clase = CapClaseIpec(capeventoperiodo_id=int(request.POST['cepid']),
                                         turno=form.cleaned_data['turno'],
                                         dia=form.cleaned_data['dia'],
                                         fechainicio=form.cleaned_data['fechainicio'],
                                         fechafin=form.cleaned_data['fechafin'])
                    clase.save(request)
                    log(u'Adiciono horario en Evento en capacitacion IPEC: %s [%s]' % (clase,clase.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editclase':
            try:
                form = CapClaseIpecForm(request.POST)
                if form.is_valid():
                    clase = CapClaseIpec.objects.get(pk=int(request.POST['claseid']))
                    if CapClaseIpec.objects.filter(capeventoperiodo=clase.capeventoperiodo, dia=clase.dia,turno=clase.turno, fechainicio=form.cleaned_data['fechainicio'],fechafin=form.cleaned_data['fechafin'], status=True).exclude(pk=clase.id).exists():
                        return JsonResponse({"result": "bad","mensaje": u"Hay una Clase que existe con las misma fechas y turno."})
                    if not form.cleaned_data['fechainicio'] >= clase.capeventoperiodo.fechainicio or not form.cleaned_data['fechafin'] <= clase.capeventoperiodo.fechafin:
                        return JsonResponse({"result": "bad","mensaje": u"Las fecha no puede ser mayor a las fecha del evento."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if form.cleaned_data['fechainicio'] == form.cleaned_data['fechafin']:
                        if not clase.dia == form.cleaned_data['fechainicio'].weekday()+1:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no concuerdan con el dia."})
                    clase.fechainicio = form.cleaned_data['fechainicio']
                    clase.fechafin = form.cleaned_data['fechafin']
                    clase.save(request)
                    log(u'Edito horario en Evento en capacitacion IPEC: %s [%s]' % (clase, clase.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delclase':
            try:
                clase = CapClaseIpec.objects.get(pk=int(request.POST['id']))
                if clase.capcabeceraasistenciaipec_set.filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar, porque tiene asistencias registradas."})
                log(u'Elimino horario en Evento en capacitacion IPEC: %s [%s]' % (clase,clase.id), request, "del")
                clase.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #ASISTENCIAS
        elif action == 'asistencia':
            try:
                asis = CapCabeceraAsistenciaIpec.objects.filter(fecha=datetime.now().date() if not 'fecha' in request.POST else datetime.strptime(request.POST["fecha"], '%d-%m-%Y'),clase_id=int(request.POST["idc"]), status=True)
                if not CapClaseIpec.objects.get(pk=int(request.POST['idc'])).capeventoperiodo.exiten_inscritos():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede continuar, porque no existen inscritos."})
                if 'fecha' in request.POST:
                    fecha=datetime.strptime(request.POST["fecha"], '%d-%m-%Y')
                    if asis.exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe asistencia en esa fecha y clase."})
                    if not CapClaseIpec.objects.filter(Q(pk=int(request.POST['idc'])),(Q(fechainicio__lte=fecha) & Q(fechafin__gte=fecha)), status=True,dia=fecha.weekday() + 1).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No esta en rango de fecha o en dia."})
                if not asis.exists():
                    clase=CapClaseIpec.objects.get(pk=int(request.POST['idc']))
                    asistencia=CapCabeceraAsistenciaIpec(clase_id=int(request.POST['idc']),
                                                         fecha= fecha.date() if 'fecha' in request.POST else datetime.now().date(),
                                                         horaentrada=clase.turno.horainicio,
                                                         horasalida=clase.turno.horafin,
                                                         contenido="SIN CONTENIDO",
                                                         observaciones="SIN OBSERVACIONES")
                    asistencia.save(request)
                    log(u'Agrego Asistencia en Capacitacion IPEC: %s [%s]' % (asistencia,asistencia.id), request, "add")
                    for integrante in clase.capeventoperiodo.inscripcion_evento_rubro_pendiente_o_cancelado():
                        resultadovalores = CapDetalleAsistenciaIpec(inscrito=integrante,cabeceraasistencia=asistencia, asistio=False)
                        resultadovalores.save(request)
                else:
                    asistencia=asis[0]
                return JsonResponse({"result": "ok",'id':asistencia.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciagrupal':
            try:
                cadenaselect = request.POST['cadenaselect']
                cadenanoselect = request.POST['cadenanoselect']
                cadenadatos = cadenaselect.split(',')
                cadenanodatos = cadenanoselect.split(',')
                asistencia=CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                for cadena in cadenadatos:
                    if cadena:
                        if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=cadena,status=True).exists():
                            resultadovalores =asistencia.capdetalleasistenciaipec_set.get(inscrito_id=cadena,status=True)
                            resultadovalores.asistio = True
                            resultadovalores.save(request)
                        else:
                            resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=cadena,cabeceraasistencia=asistencia,asistio=True)
                            resultadovalores.save(request)
                for cadenano in cadenanodatos:
                    if cadenano:
                        if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=cadenano,status=True).exists():
                            resultadovalores =asistencia.capdetalleasistenciaipec_set.get(inscrito_id=cadenano,status=True)
                            resultadovalores.asistio = False
                            resultadovalores.save(request)
                        else:
                            resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=cadenano,cabeceraasistencia=asistencia,asistio=False)
                            resultadovalores.save(request)
                log(u'Edito Asistencia en Capacitacion IPEC: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                data = {"result": "ok", "results": [{"id": x.inscrito.id, "porcientoasist": x.inscrito.porciento_asistencia_ipec(),"porcientorequerido":x.inscrito.porciento_requerido_asistencia_ipec()} for x in asistencia.capdetalleasistenciaipec_set.filter(status=True)]}
                return JsonResponse(data)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciaindividual':
            try:
                asistencia=CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=int(request.POST['idi']),status=True).exists():
                    resultadovalores =asistencia.capdetalleasistenciaipec_set.get(inscrito_id=int(request.POST['idi']),status=True)
                    resultadovalores.asistio = True if request.POST['valor']=="y" else False
                    resultadovalores.save(request)
                else:
                    resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=int(request.POST['idi']),cabeceraasistencia=asistencia,asistio=True if request.POST['valor']=="y" else False)
                    resultadovalores.save(request)
                datos={}
                datos['id'] = resultadovalores.inscrito.id
                datos['porcientoasist'] = resultadovalores.inscrito.porciento_asistencia_ipec()
                datos['porcientorequerido'] = resultadovalores.inscrito.porciento_requerido_asistencia_ipec()
                datos['result']='ok'
                log(u'Edito Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse(datos)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciacontenido':
            try:
                asistencia=CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                asistencia.contenido=request.POST["valor"]
                asistencia.save(request)
                log(u'Edito Contenido de Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciaobservacion':
            try:
                asistencia=CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                asistencia.observaciones=request.POST["valor"]
                asistencia.save(request)
                log(u'Edito Observacion de Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verdetalleevento':
                try:
                    data = {}
                    data['evento'] =CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    template = get_template("adm_capacitacioneventoperiodoipec/detalleevento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'inscritos':
                try:
                    data['title'] = u'Inscritos'
                    search = None
                    ids = None
                    eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            inscrito = eventoperiodo.capinscritoipec_set.filter(Q(participante__nombres__icontains=search) |
                                                                                Q(participante__apellido1__icontains=search) |
                                                                                Q(participante__apellido2__icontains=search) |
                                                                                Q(participante__cedula__icontains=search) |
                                                                                Q(participante__pasaporte__icontains=search)&
                                                                                Q(participante__rubro__isnull=False)&Q( participante__rubro__cancelado=True)&
                                                                                Q(participante__rubro__status=True)) \
                                                                                .distinct().order_by('participante__apellido1', 'participante__apellido2','participante__nombres')
                        else:
                            inscrito = eventoperiodo.capinscritoipec_set.filter((Q( participante__apellido1__icontains=ss[0]) & Q(participante__apellido2__icontains=ss[1])) |
                                                                                (Q(participante__nombres__icontains=ss[0]) & Q(participante__nombres__icontains=ss[1]))&
                                                                                Q(participante__rubro__isnull=False)&Q( participante__rubro__cancelado=True)&
                                                                                Q(participante__rubro__status=True)) \
                                                                                .distinct().order_by('participante__apellido1', 'participante__apellido2','participante__nombres')
                    else:
                        inscrito = eventoperiodo.capinscritoipec_set.filter(status=True, participante__rubro__isnull=False, participante__rubro__cancelado=True, participante__rubro__status=True).distinct().order_by('participante__apellido1', 'participante__apellido2', 'participante__nombres')
                    paging = MiPaginador(inscrito, 20)
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
                    data['inscritos'] = page.object_list
                    data['eventoperiodo'] = eventoperiodo
                    return render(request, "adm_capacitacioneventoperiodoipec_inst/inscritos.html", data)
                except Exception as ex:
                    pass

            if action == 'asistencia':
                try:
                    data['title'] = u'Horarios'
                    dia = 0
                    clase_activa = False
                    capeventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    semana = [[0, 'Hoy'], [1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'],[4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo'], [8, 'Todos']]
                    if 'd' in request.GET:
                        dia = int(request.GET['d'])
                        if dia == 8 :
                            data['dias'] = {1:'Lunes', 2: 'Martes', 3:'Miercoles',4:'Jueves', 5:'Viernes', 6:'Sabado', 7: 'Domingo'}
                        elif dia > 0 and dia < 8:
                            data['dias'] = {DIAS_CHOICES[dia-1][0]:  DIAS_CHOICES[dia-1][1]}
                    else:
                        clase_activa = True
                        data['fecha_hoy'] = datetime.now().date()
                        data['clases_hoy'] = capeventoperiodo.clases_activas()
                        data['dias'] = {DIAS_CHOICES[date.today().weekday()][0]: DIAS_CHOICES[date.today().weekday()][1]}
                    data['select_dia'] = dia
                    data['capeventoperiodo'] = capeventoperiodo
                    data['clase_activa'] = clase_activa
                    data['dia_list'] = semana
                    form = CapAsistenciaIpecForm()
                    form.adicionar(capeventoperiodo)
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec_inst/asistencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addasistencia':
                try:
                    revisar=False
                    data['title'] = u'Asistencia'
                    data['cabeceraasistencia'] = asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.GET['id']))
                    data['clase']= asistencia.clase
                    data['listadoinscritos'] = asistencia.clase.capeventoperiodo.inscripcion_evento_rubro_pendiente_o_cancelado()
                    if 'm' in request.GET:
                        revisar=True
                    data['revisar'] = revisar
                    return render(request, "adm_capacitacioneventoperiodoipec/addasistencia.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Planificación de Eventos'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    evento = CapEventoPeriodoIpec.objects.filter((Q(capevento__nombre__icontains=search) |
                                                                  Q(enfoque__nombre__icontains=search)) &
                                                                  Q(status=True) & Q(capinstructoripec__instructor=persona)).distinct().order_by('capevento','enfoque','fechainicio')
                else:
                    evento = CapEventoPeriodoIpec.objects.filter(Q(capevento__nombre__icontains=ss[0]) & Q(enfoque__nombre__icontains=ss[1]) &
                                                                 Q(status=True)& Q(capinstructoripec__instructor=persona)).distinct().order_by('capevento', 'enfoque', 'fechainicio')
            else:
                evento = CapEventoPeriodoIpec.objects.filter(status=True, capinstructoripec__instructor=persona).order_by('-fechainicio')
            paging = MiPaginador(evento, 20)
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
            data['evento'] = page.object_list
            # reportes
            data['reporte_0'] = obtener_reporte('inscritos_capacitacion_auth')
            data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
            return render(request, "adm_capacitacioneventoperiodoipec_inst/viewperiodoevento.html", data)