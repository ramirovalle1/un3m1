# -*- coding: UTF-8 -*-
import io
import json
import sys

import xlsxwriter
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Q, F, Count
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ResolucionForm
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdf_name
from sga.models import Aula, Clase, Nivel, Periodo, Persona, Materia, MESES_CHOICES, DIAS_CHOICES, \
    Carrera, Bloque, NivelMalla
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha
from datetime import datetime, timedelta
from django.utils import timezone
from inno.forms import HorariosAulasLaboratoriosForm, NovedadAulaForm, HorariosAulasLabEditForm, \
    DistribucionPersonalAulasForm, \
    DistribucionPersonalAulasEditForm, PantallaAulaForm, TipoNovedadForm, ReportesFechas, CierreIngresoForm, \
    CronogramaDiaNoLaborableForm, ConstatacionFisicaLaboratoriosForm
from inno.models import HorariosAulasLaboratorios, TipoNovedad, DetalleUsoAula, DetalleReservacionAulas, \
    DistribucionPersonalLaboratorio, DetalleDistribucionPersonal, PantallaAula, DetallePantallaAula, \
    CronogromaDiaNoLaborable, ConstatacionFisicaLaboratorios, ESTADO_CONSTATACION
from django.template.loader import get_template
from sga.templatetags.sga_extras import encrypt


def deltatime(param):
    pass


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']

    data['dia'] = datetime.now().date().isoweekday()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'selectaula':
            try:
                if 'id' in request.POST:
                    lista = []
                    aulas = Aula.objects.filter(status=True, bloque__id=int(request.POST['id']), clasificacion=1)
                    for aula in aulas:
                        lista.append([aula.id, aula.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'selectcarrera':
            try:
                if 'id' in request.POST:
                    lista = []
                    idcarreras = Materia.objects.filter(status=True, nivel__periodo__id=int(request.POST['id'])).values_list('asignaturamalla__malla__carrera__id', flat=True).distinct()
                    carreras = Carrera.objects.filter(status=True, id__in=idcarreras)
                    for carrera in carreras:
                        lista.append([carrera.id, carrera.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'selectmateria':
            try:
                if 'id' in request.POST:
                    lista = []
                    materias = NivelMalla.objects.filter(status=True,asignaturamalla__malla__carrera__id=int(request.POST['id'])).distinct()
                    for materia in materias:
                        lista.append([materia.id, materia.nombre])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'selectnivel':
            try:
                if 'id' in request.POST:
                    lista = []
                    materias = Materia.objects.filter( nivel__periodo__id=int(request.POST['idp']), asignaturamalla__malla__carrera__id=int(request.POST['idc']),asignatura__asignaturamalla__nivelmalla__id=int(request.POST['id'])).order_by('asignatura__nombre').distinct()
                    for materia in materias:
                        lista.append([materia.id, materia.nombre_completo_lab()])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'selectdia':
            try:
                if 'fecha' in request.POST:
                    diasemana = DIAS_CHOICES[datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date().isoweekday() - 1][1]
                    return JsonResponse({"result": "ok", 'dia':diasemana})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'addreservacion':
            try:
                with transaction.atomic():
                    fecha = datetime.now().date()
                    form = HorariosAulasLaboratoriosForm(request.POST)
                    form.edit_per(request.POST['persona'])
                    filtrodianolabo = Q(status=False)
                    if 'materia' in request.POST:
                        materia = request.POST['materia']
                        if materia:
                            form.edit_mat(request.POST['materia'], request.POST['carrera'],request.POST['nivel'])

                    if form.is_valid():
                        if materia:
                            instance = HorariosAulasLaboratorios(aula=form.cleaned_data['aula'],
                                                                persona=form.cleaned_data['persona'],
                                                                materia=form.cleaned_data['materia'],
                                                                concepto=form.cleaned_data['concepto'])
                            instance.save(request)
                            log(u'Adicionó una reservación de aulas: %s' % instance, request, "add")

                        else:
                            instance = HorariosAulasLaboratorios(aula=form.cleaned_data['aula'],
                                                                persona=form.cleaned_data['persona'],
                                                                concepto=form.cleaned_data['concepto'])
                            instance.save(request)
                            log(u'Adiciono una reservación de aulas: %s' % instance, request, "add")


                        if not 'lista_items1' in request.POST:
                            raise NameError('Debe adicionar un registro de horario')
                        for registrohora in json.loads(request.POST['lista_items1']):

                            fechainicio = datetime.strptime(registrohora['inicio'], '%Y-%m-%d').date()
                            fechafin = datetime.strptime(registrohora['fin'], '%Y-%m-%d').date()
                            horaini = datetime.strptime(registrohora['horaini'], '%H:%M').time()
                            horafin = datetime.strptime(registrohora['horafin'], '%H:%M').time()
                            examen = json.loads(registrohora['examen'])
                            dia = int(registrohora['dia'])

                            dianolaborable = CronogromaDiaNoLaborable.objects.filter(Q(Q(ffin__gte=fechainicio,
                                                                             fini__lte=fechainicio)|Q(ffin__gte=fechafin,
                                                                             fini__lte=fechafin)),status=True,activo=True).order_by('-id').first()


                            if dianolaborable:
                                # filtrodianolabo = Q(inicio__date__range=(dianolaborable.fini, dianolaborable.ffin))
                                filtrodianolabo = Q(inactivo=True)

                            if DetalleReservacionAulas.objects.filter(
                                    Q(dia=dia, horario__aula=form.cleaned_data['aula'], status=True)
                                    &((Q(inicio__date__range=(fechainicio, fechafin))
                                    |(Q(fin__date__range=(fechainicio, fechafin))))
                                    |Q(Q(inicio__date__lte=fechainicio) & Q(fin__date__gte=fechafin)))
                                    &((Q(comienza__range=(horaini, horafin)) | Q(termina__range=(horaini, horafin))) |
                                    Q(Q(comienza__lte=horaini) & Q(termina__gte=horafin)))) \
                                    .exclude(filtrodianolabo).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({'error': True,
                                                     "mensaje": f'La reservación tiene conflictos de horarios. F. Inicia: {fechainicio} - F. Fin: {fechafin} - H. Inicia: {horaini} - H. Fin: {horafin} - Dia: {DIAS_CHOICES[dia-1][1]}'}, safe=False)

                            deta = DetalleReservacionAulas(horario_id=instance.id,
                                                           inicio=fechainicio,
                                                           fin=fechafin,
                                                           comienza=horaini,
                                                           termina=horafin,
                                                           dia=dia,
                                                           examen=examen)

                            deta.save(request)
                            log(u'Adicionó detalle de horario de reservación: %s' % deta, request, "add")

                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. Detalle: %s"%(ex.__str__())}, safe=False)

        elif action == 'editreservacion':
            try:
                hi = request.POST['horainicio']
                hf = request.POST['horafin']
                horainicio = datetime.strptime(hi[0:5], '%H:%M').time()
                horafin = datetime.strptime(hf[0:5], '%H:%M').time()

                fi = datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date()
                ff = datetime.strptime(request.POST['fin'], '%Y-%m-%d').date()

                if fi > ff:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'La fecha de inicio debe ser menor a la fecha de fin'}, safe=False)

                if horainicio == horafin:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'La hora de inicio y de fin no deben ser iguales.'}, safe=False)

                if horainicio > horafin:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'La hora de inicio debe ser menor a la hora de fin.'}, safe=False)

                if DetalleReservacionAulas.objects.filter(Q(dia=int(request.POST['dia']), horario__aula__id=int(request.POST['aula']), status=True) &
                                                          (Q(inicio__range=(fi, ff)) | (Q(fin__range=(fi, ff))))
                                                          & (Q(termina__range=(horainicio, horafin)) | (Q(comienza__range=(horainicio, horafin))))).exclude(pk=request.POST['id']).exists():
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'La reservación tiene conflictos de horarios.'}, safe=False)

                f = HorariosAulasLabEditForm(request.POST)
                f.edit_per(request.POST['persona'])
                materia = ''
                if 'materia' in request.POST:
                    materia = request.POST['materia']
                    if materia:
                        f.edit_mat(request.POST['materia'], request.POST['carrera'])

                reservacion = DetalleReservacionAulas.objects.get(status=True, pk=request.POST['id'])
                if f.is_valid():
                    if materia:
                        reservacion.horario.aula = f.cleaned_data['aula']
                        reservacion.horario.persona = f.cleaned_data['persona']
                        reservacion.horario.materia = f.cleaned_data['materia']
                        reservacion.horario.concepto = f.cleaned_data['concepto']
                        reservacion.inicio = f.cleaned_data['inicio']
                        reservacion.fin = f.cleaned_data['fin']
                        reservacion.comienza = f.cleaned_data['horainicio']
                        reservacion.termina = f.cleaned_data['horafin']
                        reservacion.dia = f.cleaned_data['dia']
                        reservacion.save(request)
                        reservacion.horario.save(request)
                        log(u'Modificó la reservación: %s' % reservacion.horario, request, "edit")
                        log(u'Modificó detalle de la reservación: %s' % reservacion, request, "edit")
                    else:
                        reservacion.horario.aula = f.cleaned_data['aula']
                        reservacion.horario.persona = f.cleaned_data['persona']
                        reservacion.horario.concepto = f.cleaned_data['concepto']
                        reservacion.inicio = f.cleaned_data['inicio']
                        reservacion.fin = f.cleaned_data['fin']
                        reservacion.comienza = f.cleaned_data['horainicio']
                        reservacion.termina = f.cleaned_data['horafin']
                        reservacion.dia = f.cleaned_data['dia']
                        reservacion.save(request)
                        reservacion.horario.save(request)
                        log(u'Modificó la reservación: %s' % reservacion.horario, request, "edit")
                        log(u'Modificó detalle de la reservación: %s' % reservacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editreservaciones':
            try:
                form = HorariosAulasLaboratoriosForm(request.POST)
                id = encrypt(request.POST['id'])
                if not HorariosAulasLaboratorios.objects.filter(status=True,id=id):
                    raise NameError('No se encuentra el horario.')
                horario = HorariosAulasLaboratorios.objects.get(status=True,id=id)
                if 'materia' in request.POST:
                    materia = request.POST['materia']
                    if materia:
                        form.edit_mat(request.POST['materia'], request.POST['carrera'],request.POST['nivel'])
                if 'persona' in request.POST:
                    persona = request.POST['persona']
                    if persona:
                        form.edit_per(persona)
                if not form.is_valid():
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})
                horario.aula = form.cleaned_data['aula']
                horario.persona = form.cleaned_data['persona']
                horario.materia = form.cleaned_data['materia']
                horario.concepto = form.cleaned_data['concepto']
                horario.save(request)
                log(u"Editó el registro de horarios: %s"%horario,request,'edit')
                if not 'lista_items1' in request.POST:
                    raise NameError('Debe adicionar un registro de horario')
                listaexcluid = []
                for registrohora in json.loads(request.POST['lista_items1']):
                    fechainicio = datetime.strptime(registrohora['inicio'], '%Y-%m-%d').date()
                    fechafin = datetime.strptime(registrohora['fin'], '%Y-%m-%d').date()
                    horaini = datetime.strptime(registrohora['horaini'], '%H:%M').time()
                    horafin = datetime.strptime(registrohora['horafin'], '%H:%M').time()
                    examen = json.loads(registrohora['examen'])
                    dia = int(registrohora['dia'])
                    if DetalleReservacionAulas.objects.filter(Q(dia=dia, horario__aula__id=horario.aula.id, status=True) &
                                                              (Q(inicio__range=(fechainicio, fechafin)) | (Q(fin__range=(fechainicio, fechafin))))
                                                              & (Q(termina__range=(horaini, horafin)) | (Q(comienza__range=(horaini, horafin))))).exclude(horario=horario).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "mensaje": 'La reservación tiene conflictos de horarios.'}, safe=False)
                    if not DetalleReservacionAulas.objects.filter(Q(dia=dia, horario__aula__id=horario.aula.id, status=True) &
                                                              (Q(inicio=fechainicio) & (Q(fin=fechafin)))
                                                              & (Q(termina=horafin) & (Q(comienza=horaini)))
                                                              ,horario=horario,examen=examen).exists():
                        deta = DetalleReservacionAulas(horario_id=horario.id,
                                                       inicio=fechainicio,
                                                       fin=fechafin,
                                                       comienza=horaini,
                                                       termina=horafin,
                                                       dia=dia,
                                                       examen=examen)

                        deta.save(request)
                        listaexcluid.append(deta.id)
                        log(u'Adicionó detalle de horario de reservación: %s' % deta, request, "add")
                    else:
                        deta = DetalleReservacionAulas.objects.filter(Q(dia=dia, horario__aula__id=horario.aula.id, status=True) &
                                                              (Q(inicio=fechainicio) & (Q(fin=fechafin)))
                                                              & (Q(termina=horafin) & (Q(comienza=horaini)))
                                                              ,horario=horario,examen=examen).order_by('-id').first()
                        listaexcluid.append(deta.id)

                for delete in DetalleReservacionAulas.objects.filter(status=True,horario=horario).exclude(id__in=listaexcluid,):
                    delete.status=False
                    delete.save(request)
                    log(u'Elimino detalle de horario de reservación: %s' % deta, request, "del")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s"%ex.__str__()})

        elif action == 'addnovedad':
            try:
                with transaction.atomic():
                    form = NovedadAulaForm(request.POST)
                    hora = HorariosAulasLaboratorios.objects.get(status=True, pk=int(request.POST['id']))
                    if form.is_valid():
                        deta = DetalleUsoAula(horario=hora,
                                              clasenovedad=int(request.POST['clasi']),
                                              tiponovedad=form.cleaned_data['tiponovedad'],
                                              observacion=form.cleaned_data['observacion'])
                        deta.save(request)
                        log(u'Adiciono novedad: %s' % deta, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],"message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'adddistribucion':
            try:
                with transaction.atomic():
                    form = DistribucionPersonalAulasForm(request.POST)

                    if form.is_valid():
                        instance = DistribucionPersonalLaboratorio(bloque=form.cleaned_data['bloque'],
                                                                  encargado=form.cleaned_data['persona'])
                        instance.save(request)
                        log(u'Adicionó una distribución de personal: %s' % instance, request, "add")

                        if not 'lista_items1' in request.POST:
                            raise NameError('Debe adicionar un registro de horario')

                        for registrohora in json.loads(request.POST['lista_items1']):
                            fechainicio = datetime.strptime(registrohora['inicio'], '%Y-%m-%d').date()
                            fechafin = datetime.strptime(registrohora['fin'], '%Y-%m-%d').date()
                            horaini = datetime.strptime(registrohora['horaini'], '%H:%M').time()
                            horafin = datetime.strptime(registrohora['horafin'], '%H:%M').time()
                            aula = int(registrohora['aula'])

                            # if DetalleDistribucionPersonal.objects.filter(Q(aula_id=aula, status=True) &
                            #                                           (Q(inicio__range=(fechainicio, fechafin)) | (Q(fin__range=(fechainicio, fechafin))))
                            #                                           & (Q(termina__range=(horaini, horafin)) | (Q(comienza__range=(horaini, horafin))))).exists():
                            #     transaction.set_rollback(True)
                            #     return JsonResponse({'error': True, "mensaje": 'La reservación tiene conflictos de horarios.'}, safe=False)

                            deta = DetalleDistribucionPersonal(distribucion_id=instance.id,
                                                               aula_id=aula,
                                                               inicio=fechainicio,
                                                               fin=fechafin,
                                                               comienza=horaini,
                                                               termina=horafin)

                            deta.save(request)
                            log(u'Adicionó detalle de horario de distribución: %s' % deta, request, "add")

                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editdistribucion':
            try:
                hi = request.POST['horainicio']
                hf = request.POST['horafin']
                horainicio = datetime.strptime(hi[0:5], '%H:%M').time()
                horafin = datetime.strptime(hf[0:5], '%H:%M').time()

                fi = datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date()
                ff = datetime.strptime(request.POST['fin'], '%Y-%m-%d').date()

                if fi > ff:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'La fecha de inicio debe ser menor a la fecha de fin'}, safe=False)

                if horainicio == horafin:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'La hora de inicio y de fin no deben ser iguales.'}, safe=False)

                if horainicio > horafin:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'La hora de inicio debe ser menor a la hora de fin.'}, safe=False)

                if DetalleDistribucionPersonal.objects.filter(Q(aula__id=int(request.POST['aula']), status=True) &
                                                          (Q(inicio__range=(fi, ff)) | (Q(fin__range=(fi, ff))))
                                                          & (Q(termina__range=(horainicio, horafin)) | (Q(comienza__range=(horainicio, horafin))))).exclude(pk=request.POST['id']).exists():
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, "mensaje": 'La distribución tiene conflictos de horarios.'}, safe=False)

                f = DistribucionPersonalAulasEditForm(request.POST)

                distribuido = DetalleDistribucionPersonal.objects.get(status=True, pk=request.POST['id'])
                if f.is_valid():
                    distribuido.distribucion.bloque = f.cleaned_data['bloque']
                    distribuido.distribucion.encargado = f.cleaned_data['persona']
                    distribuido.aula = f.cleaned_data['aula']
                    distribuido.inicio = f.cleaned_data['inicio']
                    distribuido.fin = f.cleaned_data['fin']
                    distribuido.comienza = f.cleaned_data['horainicio']
                    distribuido.termina = f.cleaned_data['horafin']
                    distribuido.save(request)
                    distribuido.distribucion.save(request)
                    log(u'Modificó la distribución: %s' % distribuido.distribucion, request, "edit")
                    log(u'Modificó detalle de la distribución: %s' % distribuido, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletedisttribucion':
            try:
                distribuido = DetalleDistribucionPersonal.objects.get(status=True, pk=int(encrypt(request.POST['id'])))
                distribuido.status = False
                distribuido.save(request)
                log(u'Elimino detalle de distribución: %s' % distribuido, request, "deldistribucion")
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deletereservacion':
            try:
                reservacion = HorariosAulasLaboratorios.objects.get(status=True, pk=int(encrypt(request.POST['id'])))
                reservacion.status = False
                reservacion.save(request)
                detallereservcion = reservacion.detallereservacionaulas_set.filter(status=True)
                for detal in detallereservcion:
                    detal.status = False
                    detal.save(request)
                log(u'Elimino reservación: %s' % reservacion, request, "delreservacion")
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addpantallaaula':
            try:
                f = PantallaAulaForm(request.POST)
                aulas = request.POST.getlist('aula')
                if not len(aulas) > 0:
                    raise NameError(u'Debe seleccionar al menos una aula.')
                if not f.is_valid():
                    raise NameError(str(f.errors))
                pantalla = PantallaAula(
                    descripcion = f.cleaned_data['descripcion']
                )
                log(u'Agrego pantalla de visualización %s' % pantalla, request, 'add')
                pantalla.save(request)
                for aul in aulas:
                    if Aula.objects.values('id').filter(id=aul,status=True).exists():
                        aula = Aula.objects.get(id=aul,status=True)
                        det = DetallePantallaAula(
                            pantallaaula = pantalla,
                            aula = aula
                        )
                        det.save(request)
                        log(u'Agrego detalle de pantalla %s' % det,request,'add')
                res_json = {'result': False, "mensaje": "Registro guardado con exito"}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'result': True, "mensaje": "Error: {}".format(ex)}
            return JsonResponse(res_json)

        elif action == 'editpantallaaula':
            try:
                f = PantallaAulaForm(request.POST)
                aulas = request.POST.getlist('aula')
                id = encrypt(request.POST['id'])
                if not len(aulas) > 0:
                    raise NameError(u'Debe seleccionar al menos una aula.')
                if not f.is_valid():
                    raise NameError(str(f.errors))
                pantalla = PantallaAula.objects.get(id =id)
                log(u'Agrego pantalla de visualización %s' % pantalla, request, 'add')
                pantalla.save(request)
                listaexlui=[]
                for aul in aulas:
                    if Aula.objects.values('id').filter(id=aul,status=True).exists():
                        aula = Aula.objects.get(id=aul,status=True)
                        if not DetallePantallaAula.objects.filter(status=True,pantallaaula=pantalla,aula=aula):
                            det = DetallePantallaAula(
                                pantallaaula = pantalla,
                                aula = aula
                            )
                            det.save(request)
                            listaexlui.append(det.id)
                            log(u'Agrego detalle de pantalla %s' % det,request,'add')
                        else:
                            det = DetallePantallaAula.objects.filter(status=True,pantallaaula=pantalla,aula=aula).order_by('-id').first()
                            listaexlui.append(det.id)
                det = DetallePantallaAula.objects.filter(status=True,pantallaaula=pantalla).exclude(id__in=listaexlui)
                for dele in det:
                    dele.status=False
                    dele.save(request)
                    log(u'Eliminó detalle de pantalla visualizacion %s'%dele,request,'del')

                res_json = {'result': False, "mensaje": "Registro guardado con exito"}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'result': True, "mensaje": "Error: {}".format(ex)}
            return JsonResponse(res_json)

        elif action == 'deletepantallaaula':
            with transaction.atomic():
                try:
                    reservacion = PantallaAula.objects.get(status=True, pk=int(encrypt(request.POST['id'])))
                    reservacion.status = False
                    reservacion.save(request)
                    log(u'Elimino pantala: %s' % reservacion, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        elif action == 'registrar_ingreso':
            try:
                id = encrypt(request.POST['id'])
                obs = request.POST.get('obs')
                fecha = datetime.now().date()
                hora = datetime.now().time()
                horafin = datetime.now()
                if not DetalleReservacionAulas.objects.values('id').filter(status=True,id=id).exists():
                    return JsonResponse({'result':False,'mensaje':"El registro no existe, intentelo mas tarde."})
                detreservacion = DetalleReservacionAulas.objects.get(status=True,id=id)
                if detreservacion.dia != fecha.isoweekday():
                    raise NameError(u"No puede registrar novedad fuera del día de reservación")
                # if detreservacion.comienza > hora or detreservacion.termina < (horafin- timedelta(minutes=10)).time():
                #     raise NameError(u"No puede registrar novedad fuera del horario de reservación")
                usoaula = detreservacion.detalleusoaula_set.filter(status=True,clasenovedad=1)
                if usoaula.filter(fecha_creacion__date__range=(fecha,fecha + timedelta(1)),detallehorario__dia=fecha.isoweekday(),).exists():
                    uso = usoaula.filter(fecha_creacion__date__range=(fecha,fecha + timedelta(1)),detallehorario__dia=fecha.isoweekday(),).order_by('-id').first()
                    uso.observacion = obs
                    uso.save(request)
                    log(u"Edito el registro de ingreso %s" % uso.__str__(),request,"add")
                else:
                    uso = DetalleUsoAula(
                        detallehorario = detreservacion,
                        horario = detreservacion.horario,
                        clasenovedad = 1,
                        observacion = obs
                    )
                    uso.save(request)
                    log("Agrego registro de ingreso %s" % uso.__str__(),request,"add")
                return JsonResponse({'result':True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':False,'mensaje':"Error al procesar los datos. Detalle: %s"%(ex.__str__())})

        elif action == 'registrar_novedad_ingreso':
            try:
                id = encrypt(request.POST['id'])
                tipo = int(encrypt(request.POST.get('tipo')))
                observacion = request.POST.get('desc')
                fecha = datetime.now().date()
                hora = datetime.now().time()
                horafin = datetime.now()
                if not DetalleReservacionAulas.objects.values('id').filter(status=True, id=id).exists():
                    return JsonResponse({'result': False, 'mensaje': "El registro no existe, intentelo mas tarde."})
                detreservacion = DetalleReservacionAulas.objects.get(status=True, id=id)
                if detreservacion.dia != fecha.isoweekday():
                    raise NameError(u"No puede registrar novedad fuera del día de reservación")
                # if detreservacion.comienza > hora or detreservacion.termina < (horafin- timedelta(minutes=10)).time():
                #     raise NameError(u"No puede registrar novedad fuera del horario de reservación")
                usoaula = detreservacion.detalleusoaula_set.filter(status=True, clasenovedad=1)
                if usoaula.filter(fecha_creacion__date__range=(fecha, fecha + timedelta(1)), detallehorario__dia=fecha.isoweekday(), ).exists():
                    uso = usoaula.filter(fecha_creacion__date__range=(fecha, fecha + timedelta(1)), detallehorario__dia=fecha.isoweekday(),).order_by('-id').first()
                    uso.tiponovedad_id = tipo
                    if tipo != 1:
                        uso.observacion = observacion
                    uso.save(request)
                    log(u"Edito el registro de ingreso %s" % uso.__str__(),request,"add")
                else:
                    uso = DetalleUsoAula(
                        detallehorario = detreservacion,
                        horario = detreservacion.horario,
                        clasenovedad = 1,
                        tiponovedad_id= tipo
                    )
                    if tipo != 1:
                        uso.observacion = observacion
                    uso.save(request)
                    log("Agrego registro de ingreso %s" % uso.__str__(),request,"add")
                return JsonResponse({'result': True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':False,'mensaje':"Error al procesar los datos. Detalle: %s"%(ex.__str__())})

        elif action == 'registrar_salida':
            try:
                id = encrypt(request.POST['id'])
                obs = request.POST.get('obs')
                fecha = datetime.now().date()
                # tipo = int(encrypt(request.POST.get('tipo')))
                hora = datetime.now().time()
                horafin = datetime.now()
                if not DetalleReservacionAulas.objects.values('id').filter(status=True, id=id).exists():
                    return JsonResponse({'result': False, 'mensaje': "El registro no existe, intentelo mas tarde."})
                detreservacion = DetalleReservacionAulas.objects.get(status=True, id=id)
                if detreservacion.dia != fecha.isoweekday():
                    raise NameError(u"No puede registrar novedad fuera del día de reservación")
                # if detreservacion.comienza > hora or detreservacion.termina < (horafin - timedelta(minutes=10)).time():
                #     raise NameError(u"No puede registrar novedad fuera del horario de reservación")
                usoaula = detreservacion.detalleusoaula_set.filter(status=True, clasenovedad=2)
                if usoaula.filter(fecha_creacion__date__range=(fecha,fecha + timedelta(1)),detallehorario__dia=fecha.isoweekday(),).exists():
                    uso = usoaula.filter(fecha_creacion__date__range=(fecha,fecha + timedelta(1)),detallehorario__dia=fecha.isoweekday(),).order_by('-id').first()
                    # uso.tiponovedad_id = tipo
                    # if tipo != 1:
                    uso.observacion = obs
                    uso.save(request)
                    log(u"Edito el registro de salida %s" % uso.__str__(),request,"add")
                else:
                    uso = DetalleUsoAula(
                        detallehorario = detreservacion,
                        horario = detreservacion.horario,
                        clasenovedad = 2,
                        # tiponovedad_id = tipo
                    )
                    # if tipo != 1:
                    uso.observacion = obs
                    uso.save(request)
                    log("Agrego registro de salida %s" % uso.__str__(),request,"add")
                return JsonResponse({'result':True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'mensaje': "Error al procesar los datos. Detalle: %s" % (ex.__str__())})

        elif action == 'registrar_novedad_salida':
            try:
                id = encrypt(request.POST['id'])
                tipo = int(encrypt(request.POST.get('tipo')))
                observacion = request.POST.get('desc')
                fecha = datetime.now().date()
                hora = datetime.now().time()
                horafin = datetime.now()
                if not DetalleReservacionAulas.objects.values('id').filter(status=True, id=id).exists():
                    return JsonResponse({'result': False, 'mensaje': "El registro no existe, intentelo mas tarde."})
                detreservacion = DetalleReservacionAulas.objects.get(status=True, id=id)
                if detreservacion.dia != fecha.isoweekday():
                    raise NameError(u"No puede registrar novedad fuera del día de reservación")
                # if detreservacion.comienza > hora or detreservacion.termina < (horafin - timedelta(minutes=10)).time():
                #     raise NameError(u"No puede registrar novedad fuera del horario de reservación")
                usoaula = detreservacion.detalleusoaula_set.filter(status=True, clasenovedad=2)
                if usoaula.filter(fecha_creacion__date__range=(fecha, fecha + timedelta(1)), detallehorario__dia=fecha.isoweekday(),).exists():
                    uso = usoaula.filter(fecha_creacion__date__range=(fecha, fecha + timedelta(1)), detallehorario__dia=fecha.isoweekday(),).order_by('-id').first()
                    uso.tiponovedad_id = tipo
                    uso.observacion = observacion
                    uso.save(request)
                    log(u"Edito el registro de salida %s" % uso.__str__(), request, "add")
                else:
                    uso = DetalleUsoAula(
                        detallehorario=detreservacion,
                        horario=detreservacion.horario,
                        clasenovedad=2,
                        tiponovedad_id=tipo,
                        observacion = observacion
                    )
                    uso.save(request)
                    log("Agrego registro de salida %s" % uso.__str__(), request, "add")
                return JsonResponse({'result': True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'mensaje': "Error al procesar los datos. Detalle: %s" % (ex.__str__())})

        elif action == 'addtiponovedad':
            try:
                f = TipoNovedadForm(request.POST)
                if not f.is_valid():
                    raise NameError(f"%s"%[{k: v[0]} for k,v in f.errors.items()])
                tipo = TipoNovedad(
                    descripcion = f.cleaned_data['descripcion']
                )
                tipo.save(request)
                log(u"Agrego tipo de novedad %s"%tipo,request,'add')
                return JsonResponse({'result':False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True,'mensaje':'Error al procesar los datos. Detalle: %s'% ex.__str__()})

        elif action == 'edittiponovedad':
            try:
                id = encrypt(request.POST['id'])
                if not TipoNovedad.objects.values('id').filter(status=True,id=id).exists():
                    raise NameError("No se encontro el registro.")
                tipo = TipoNovedad.objects.get(status=True,id=id)
                f = TipoNovedadForm(request.POST)
                if not f.is_valid():
                    raise NameError("%s"%[{k: v[0]} for k,v in f.errors.items()])
                tipo.descripcion = f.cleaned_data['descripcion']
                tipo.save(request)
                log(u"Edito tipo de novedad %s"%tipo,request,'add')
                return JsonResponse({'result':False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':True,'mensaje':'Error al procesar los datos. Detalle: %s'% ex.__str__()})

        elif action == 'deletetiponovedad':
            try:
                id = encrypt(request.POST['id'])
                if not TipoNovedad.objects.values('id').filter(status=True,id=id).exists():
                    raise NameError("No se encontro el registro.")
                tipo = TipoNovedad.objects.get(status=True, id=id)
                tipo.status=False
                tipo.save(request)
                log("Elimino tipo novedad: %s"%tipo,request,'del')
                return JsonResponse({'error':False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error':True,'messages':u'Error al procesar los datos. Detalle: %s'% ex.__str__()})

        elif action == 'excel_registrohorarios':
            try:
                if DistribucionPersonalLaboratorio.objects.filter(status=True, encargado=persona).order_by(
                        '-id').exists():
                    bloque = DistribucionPersonalLaboratorio.objects.filter(status=True, encargado=persona).order_by(
                        '-id').first()
                    aulas = bloque.bloque.aula_set.values_list('id', flat=True).filter(status=True).distinct()
                form = ReportesFechas(request.POST)
                form.reservas_horarios()
                if not form.is_valid():
                    raise NameError("%s"%[{k: v[0]} for k,v in form.errors.items()])
                data['desde'] = desde = form.cleaned_data['desde']
                data['hasta'] = hasta = form.cleaned_data['hasta']
                data['fechaactual'] = fechaactual = datetime.now()
                data['aula'] = aula = form.cleaned_data['aula']
                data['usuario'] = persona
                if desde > hasta:
                    raise NameError("La fecha desde debe ser mayor que la fecha hasta")
                qfiltros = Q(status=True) & Q(inicio__date__gte=desde) & Q(fin__date__lte=hasta)
                if aulas:
                    if aula:
                        qfiltros = qfiltros & Q(horario__aula=aula)
                    else:
                        qfiltros = qfiltros & Q(horario__aula__in=aulas)
                filtro = DetalleReservacionAulas.objects.filter(qfiltros).distinct()
                data['total'] = len(filtro)
                data['filtro'] = filtro
                return conviert_html_to_pdf_name(
                    'adm_laboratorioscomputacion/registrohorarios.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    },
                    f'reporte_horarios_{fechaactual.strftime("%d_%m_%Y")}'
                )
            except Exception as ex:
                return JsonResponse({'result':True,'mensaje':'Error al procesar los datos. Detalle: %s'% ex.__str__()})

        elif action == 'excel_revisionsalas':
            try:
                aulas,bloque = None,None
                if DistribucionPersonalLaboratorio.objects.filter(status=True, encargado=persona).order_by(
                        '-id').exists():
                    bloque = DistribucionPersonalLaboratorio.objects.filter(status=True, encargado=persona).order_by(
                        '-id').first()
                    data['bloque'] = bloque.bloque
                    aulas = bloque.bloque.aula_set.values_list('id', flat=True).filter(status=True).distinct()

                valores = []
                form = ReportesFechas(request.POST)
                if not form.is_valid():
                    raise NameError("%s"%[{k: v[0]} for k,v in form.errors.items()])
                data['desde'] = desde = form.cleaned_data['desde']
                data['hasta'] = hasta = form.cleaned_data['hasta']
                data['aula'] = aula = form.cleaned_data['aula']
                data['fechaactual'] = fechaactual = datetime.now()
                tipono= form.cleaned_data['tiponovedad']

                data['usuario'] = persona
                qfiltros = Q(status=True)&Q(fecha_creacion__date__gte=desde)&Q(fecha_creacion__date__lte=hasta)
                if aulas:
                    if aula:
                        qfiltros = qfiltros & Q(horario__aula=aula)
                    else:
                        qfiltros=qfiltros & Q(horario__aula__in=aulas)
                if desde > hasta:
                    raise NameError("La fecha desde debe ser mayor que la fecha hasta")
                id_valida = DetalleUsoAula.objects.filter(qfiltros).filter(clasenovedad=1,usuario_creacion=persona.usuario).values_list('id',flat=True)
                filtro = DetalleUsoAula.objects.filter(qfiltros).filter(id__in=id_valida).order_by('fecha_creacion__date','detallehorario__comienza','horario__aula').distinct('detallehorario__comienza','fecha_creacion__date','horario__aula')
                id_ingreso = []
                id_salidas = []
                id_ingreso_ft = []
                id_salida_ft = []
                for ing_sali in filtro:
                    if ing_sali.detalle_ingreso():
                        id_ingreso.append(ing_sali.detalle_ingreso().id)
                    if ing_sali.detalle_salida():
                        id_salidas.append(ing_sali.detalle_salida().id)
                fil_ingreso =Q(tiponovedad_id=2)&Q(fecha_creacion__time__gt=F('detallehorario__comienza')+ timezone.timedelta(minutes=15))
                fil_ingreso_con_nov = ~Q(tiponovedad_id=2)&Q(fecha_creacion__time__gt=F('detallehorario__comienza')+ timezone.timedelta(minutes=15))
                fil_salida = Q(tiponovedad_id=2)&Q(fecha_creacion__time__gt=F('detallehorario__termina')+ timezone.timedelta(minutes=15))
                fil_salida_con_nov = ~Q(tiponovedad_id=2)&Q(fecha_creacion__time__gt=F('detallehorario__termina')+ timezone.timedelta(minutes=15))
                fuera_time_ingreso = DetalleUsoAula.objects.filter(status=True,id__in=id_ingreso).filter(fil_ingreso)
                fuera_time_salida = DetalleUsoAula.objects.filter(status=True,id__in=id_salidas).filter(fil_salida)
                fuera_time_in_novedad = DetalleUsoAula.objects.filter(status=True,id__in=id_ingreso).filter(fil_ingreso_con_nov)
                fuera_time_out_novedad = DetalleUsoAula.objects.filter(status=True,id__in=id_salidas).filter(fil_salida_con_nov)
                data['fuera_tiempo'] = fuera_tiempo = len(fuera_time_ingreso)+len(fuera_time_salida)
                data['fuera_tiempo_novedad'] = len(fuera_time_in_novedad)+len(fuera_time_out_novedad)
                total_ingreso = len(id_ingreso)
                total_salida = len(id_salidas)
                data['total_asignadas'] = total_ingreso+total_salida
                data['sinrealizar'] = abs(total_ingreso-total_salida)
                data['filtro'] = filtro
                data['rev_optimas'] = abs((total_ingreso+total_salida)-fuera_tiempo)
                # for tipo in tipono:
                #     valores.append([tipo.id,len(filtro.filter(tiponovedad=tipo))])
                # if valores:
                #     data['valores'] = valores
                # total = 0
                # for val in valores:
                #     total +=val[1]
                # data['total'] = total
                return conviert_html_to_pdf_name(
                    'adm_laboratorioscomputacion/revisionsalas.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    },
                    f'revision_salas_{fechaactual.strftime("%d_%m_%Y")}'
                )
            except Exception as ex:
                return JsonResponse({'result':True,'mensaje':'Error al procesar los datos. Detalle: %s'% ex.__str__()})

        elif action == 'editingresosalida':
            try:
                id = encrypt(request.POST['id'])
                if not DetalleUsoAula.objects.values('id').filter(status=True, id=id).exists():
                    raise NameError("No se encontro el registro.")
                tipo = DetalleUsoAula.objects.get(status=True, id=id)
                f = CierreIngresoForm(request.POST)
                if not f.is_valid():
                    raise NameError("%s" % [{k: v[0]} for k, v in f.errors.items()])
                tipo.observacion = f.cleaned_data['observacion']
                tipo.tiponovedad = f.cleaned_data['tiponovedad']
                tipo.clasenovedad = f.cleaned_data['clasenovedad']
                tipo.save(request)
                log(u"Edito el ingreso-cierre %s" % tipo, request, 'edit')
                return JsonResponse({'result': False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': 'Error al procesar los datos. Detalle: %s' % ex.__str__()})

        elif action == 'addcronograma':
            try:
                form = CronogramaDiaNoLaborableForm(request.POST)
                lista = json.loads(request.POST['lista_items1'])
                if len(lista) <= 0:
                    raise NameError("No hay reservaciones en las fechas especificadas!")
                if not form.is_valid():
                    raise NameError("%s" % [{k: v[0]} for k, v in form.errors.items()])
                if form.cleaned_data['fini'] >form.cleaned_data['ffin']:
                    raise NameError(u"La fecha fin debe ser mayor que la fecha de inicio")
                crono = CronogromaDiaNoLaborable(
                    motivo=form.cleaned_data['motivo'],
                    fini=form.cleaned_data['fini'],
                    ffin=form.cleaned_data['ffin'],
                    activo=True
                )
                crono.save(request)
                for list in lista:
                    det = DetalleReservacionAulas.objects.get(status=True,id=int(encrypt(list['id'])))
                    det.inactivo = json.loads(list['check'])
                    det.save(request)
                log(u"Agrego cronocrama dia no laborable: %s" % (crono.__str__()),request,'add')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': 'Error al procesar los datos. Detalle: %s' % ex.__str__()})

        elif action == 'editcronograma':
            try:
                id = encrypt(request.POST['id'])
                crono = CronogromaDiaNoLaborable.objects.get(status=True, id=id)
                form = CronogramaDiaNoLaborableForm(request.POST)
                lista = json.loads(request.POST['lista_items1'])
                if len(lista) <= 0:
                    raise NameError("No hay reservaciones en las fechas especificadas!")
                if not form.is_valid():
                    raise NameError("%s" % [{k: v[0]} for k, v in form.errors.items()])
                if form.cleaned_data['fini'] >form.cleaned_data['ffin']:
                    raise NameError(u"La fecha fin debe ser mayor que la fecha de inicio")
                crono.motivo=form.cleaned_data['motivo']
                crono.fini=form.cleaned_data['fini']
                crono.ffin=form.cleaned_data['ffin']
                crono.save(request)
                # Almacenar detalle
                for list in lista:
                    det = DetalleReservacionAulas.objects.get(status=True, id=int(encrypt(list['id'])))
                    det.inactivo = json.loads(list['check'])
                    det.save(request)
                # Almacenar detalle
                log(u"Edita cronocrama dia no laborable: %s" % (crono.__str__()),request,'edit')
                return JsonResponse({'result': 'ok'})
                # return JsonResponse({'result': False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': 'Error al procesar los datos. Detalle: %s' % ex.__str__()})

        elif action == 'deletecronograma':
            try:
                id = encrypt(request.POST['id'])
                if not CronogromaDiaNoLaborable.objects.values('id').filter(status=True,id=id).exists():
                    raise NameError("No se encontro el registro.")
                crono = CronogromaDiaNoLaborable.objects.get(status=True, id=id)
                crono.status=False
                crono.save(request)
                log("Elimino tipo novedad: %s"%crono,request,'del')
                return JsonResponse({'error':False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error':True,'messages':u'Error al procesar los datos. Detalle: %s'% ex.__str__()})

        elif action == 'cambiarestado':
            try:
                id = encrypt(request.POST['id'])
                estado = json.loads(request.POST['est'].lower())
                crono =CronogromaDiaNoLaborable.objects.get(status=True, id=id)
                crono.activo = not estado
                crono.save(request)
                log('Actualizo el estado activo del registro: %s' % crono, request,'edit')
                return JsonResponse({'result': True,'mensaje':'Registro guardado con exito!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'mensaje': 'Error al procesar los datos. Detalle: %s' % ex.__str__()})

        elif action == 'ocultarrevisionsala':
            try:
                id_ingreso = int(encrypt(request.POST['idi']))
                id_cierre = int(encrypt(request.POST['idf']))
                id = int(encrypt(request.POST['idd']))
                detallecierre = DetalleReservacionAulas.objects.get(status=True,id=id)
                valor = json.loads(request.POST['valor'])

                detallecierre.oculto = valor
                detallecierre.save(request)
                log("Oculto el registro %s" % (detallecierre), request, 'edit')
                detuso_ingreso = DetalleUsoAula.objects.get(status=True,id=id_ingreso)
                detuso_ingreso.oculto = valor
                detuso_ingreso.save(request)
                log("Oculto el registro %s"%(detuso_ingreso),request,'edit')
                detuso_cierre = DetalleUsoAula.objects.get(status=True,id=id_cierre)
                detuso_cierre.oculto = valor
                detuso_cierre.save(request)
                log("Oculto el registro %s"%(detuso_cierre),request,'edit')
                res_js = {'result': True,'mensaje':'Registro guardado con exito!'}
            except Exception as ex:
                transaction.set_rollback(True)
                res_js = {'result': False, 'mensaje': 'Error al procesar los datos. Detalle: %s' % ex.__str__()}
            return JsonResponse(res_js)

        elif action == 'addinventario':
            try:
                form = ConstatacionFisicaLaboratoriosForm(request.POST)
                if not form.is_valid():
                    raise NameError("%s" % [{k: v[0]} for k, v in form.errors.items()])
                id_activo = form.cleaned_data['activo']
                id_activo = form.cleaned_data['activo']
                if 'activo_sel' in request.POST:
                    id_activo = int(request.POST['activo_sel'])
                    if id_activo == 0:
                        raise NameError("Seleccione un activo")
                registro = ConstatacionFisicaLaboratorios(
                    activo_id=id_activo,
                    aula=form.cleaned_data['aula'],
                    estado=form.cleaned_data['estado'],
                    fecha_constata=form.cleaned_data['fecha_constata'],
                    hora_constata=form.cleaned_data['hora_constata'],
                    observacion=form.cleaned_data['observacion']
                )
                registro.save(request)
                log("Agrego inventario de laboratorios: %s"%registro.__str__(),request,'add')
                res_js = {"result": False}
            except Exception as ex:
                transaction.set_rollback(True)
                line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                print(line_error)
                res_js = {"result": True, "mensaje": "Ocurrio un error!. Detalle: %s" % ex.__str__(),
                          "line_erro": line_error}
            return JsonResponse(res_js)


        elif action == 'editinventario':
            try:
                id = int(encrypt(request.POST['id']))
                filtro = ConstatacionFisicaLaboratorios.objects.get(id=id,status=True)
                form = ConstatacionFisicaLaboratoriosForm(request.POST)
                if not form.is_valid():
                    raise NameError("%s" % [{k: v[0]} for k, v in form.errors.items()])
                id_activo = form.cleaned_data['activo']
                if 'activo' in request.POST:
                    id_activo = int(request.POST['activo'])
                    if id_activo == 0:
                        raise NameError("Seleccione un activo")
                filtro.activo_id=id_activo
                filtro.aula=form.cleaned_data['aula']
                filtro.estado=form.cleaned_data['estado']
                filtro.fecha_constata=form.cleaned_data['fecha_constata']
                filtro.hora_constata=form.cleaned_data['hora_constata']
                filtro.observacion=form.cleaned_data['observacion']
                filtro.save(request)
                log("Edito inventario de laboratorios: %s" % filtro.__str__(), request, 'change')
                res_js = {"result": False}
            except Exception as ex:
                transaction.set_rollback(True)
                line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                print(line_error)
                res_js = {"result": True, "mensaje": "Ocurrio un error!. Detalle: %s" % ex.__str__(),"line_erro": line_error}
            return JsonResponse(res_js)

        elif action == 'delinventario':
            try:
                id = int(encrypt(request.POST['id']))
                filtro = ConstatacionFisicaLaboratorios.objects.get(id=id, status=True)
                filtro.status = False
                filtro.save(request)
                log("Elimino inventario de laboratorios: %s" % filtro.__str__(), request, 'del')
                res_js = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                print(line_error)
                res_js = {"error": True, "mensaje": "Ocurrio un error!. Detalle: %s" % ex.__str__(),"line_erro": line_error}
            return JsonResponse(res_js)

        elif action == 'viewallhide':
            try:
                lista_ids = json.loads(request.POST['ids'])
                for det in lista_ids:
                    detalle = DetalleReservacionAulas.objects.get(status=True,id=det)
                    detalle.oculto = False
                    detalle.save(request)
                log("Edito los registro para visualizar los ocultos", request, 'change')
                res_js = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                print(line_error)
                res_js = {"error": True, "mensaje": "Ocurrio un error!. Detalle: %s" % ex.__str__(),"line_erro": line_error}
            return JsonResponse(res_js)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'reservacionaulas':
                try:
                    data['title'] = 'Configuración de Aulas'
                    url_vars = '&action=reservacionaulas'
                    bloque_search, aula_search, docente_search = request.GET.get('bloque'), request.GET.get('aula'), request.GET.get('s')
                    filtro = Q(status=True)
                    filtro_aulas = Q(status=True)
                    if DistribucionPersonalLaboratorio.objects.filter(status=True,encargado=persona).order_by('-id').exists():
                        bloques = persona.distribucionpersonallaboratorio_set.filter(status=True).values_list('bloque',flat=True)
                        bloque = DistribucionPersonalLaboratorio.objects.filter(status=True,encargado=persona).order_by('-id').first()
                        aulas = bloque.bloque.aula_set.values_list('id',flat=True).filter(status=True).distinct()
                    else:
                        messages.warning(request,"No tiene aulas asignadas")
                        return HttpResponseRedirect('/adm_laboratorioscomputacion')

                    if docente_search:
                        ss = docente_search.split(" ")
                        if len(ss) > 1:
                            filtro = filtro & \
                                     Q(persona__nombres__icontains = docente_search) | \
                                     Q(persona__apellido1=ss[0]) | \
                                     Q(persona__apellido2=ss[1]) | \
                                     Q(persona__cedula=ss[0]) | \
                                    Q(materia__alias = docente_search)
                        else:
                            filtro = filtro & \
                                     Q(persona__nombres__icontains = docente_search) | \
                                     Q(persona__apellido1=docente_search) | \
                                     Q(persona__apellido2=docente_search) | \
                                     Q(persona__cedula=docente_search) | \
                                    Q(materia__alias = docente_search)
                        url_vars +=f'&s={docente_search}'
                        data['s'] = docente_search
                    if aula_search:
                        if int(aula_search) > 0:
                            filtro = filtro & Q(aula__id = aula_search)
                            data['aula'] = int(aula_search)
                            url_vars +='&aula='+aula_search
                    if bloque_search:
                        if int(bloque_search) > 0:
                            filtro = filtro & Q(aula__bloque__id=bloque_search)
                            filtro_aulas = filtro_aulas & Q(bloque__id=bloque_search)
                            data['bloque'] = int(bloque_search)
                            url_vars += '&bloque=' + bloque_search


                    reservaciones = HorariosAulasLaboratorios.objects.filter(status=True,aula__bloque__in=bloques).filter(filtro).order_by('-id')
                    paging = MiPaginador(reservaciones, 10)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['reservaciones'] = page.object_list
                    data['url_vars'] = url_vars
                    data['tiponovedad'] = TipoNovedad.objects.filter(status=True).order_by('id', 'descripcion')
                    data['bloques'] = bloques = Bloque.objects.filter(status=True, tiene_lab=True, id=bloque.bloque.id)
                    data['aulas'] = aulas_sea = Aula.objects.filter(status=True, bloque__tiene_lab=True, bloque_id=bloque.bloque.id).filter(filtro_aulas)

                    # data['modulos'] = GestionPermisos.objects.values_list('modulo_id', 'modulo__nombre', 'modulo__url').filter(status=True).distinct()
                    return render(request, "adm_laboratorioscomputacion/configuracionaula.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'addreservacion':
                try:
                    data['title'] = u'Adicionar rerservación de aulas'
                    weekday = DIAS_CHOICES[datetime.now().date().isoweekday() - 1][1]
                    form = HorariosAulasLaboratoriosForm(initial={'dia':weekday})
                    data['form'] = form
                    bloque = DistribucionPersonalLaboratorio.objects.filter(status=True, encargado=persona).order_by('-id').first()
                    form.fields['periodo'].queryset = Periodo.objects.filter(status=True).order_by('-id')
                    form.fields['periodo'].initial = periodo
                    if bloque.bloque:
                        form.fields['bloque'].initial = bloque.bloque
                    carreras = Materia.objects.values_list('asignaturamalla__malla__carrera__id',flat=True).filter(status=True,nivel__periodo=periodo).distinct()
                    form.fields['carrera'].queryset = Carrera.objects.filter(status=True, id__in=carreras)
                    return render(request, "adm_laboratorioscomputacion/addconfig.html", data)
                except Exception as ex:
                    pass

            elif action == 'editreservacion':
                try:
                    data['title'] = u'Editar rerservación de aulas'
                    data['reservacion'] = reservacion = DetalleReservacionAulas.objects.get(status=True, pk=request.GET['id'])
                    # weekday = DIAS_CHOICES[datetime.now().date().isoweekday() - 1][1]
                    if reservacion.horario.materia:
                        form = HorariosAulasLabEditForm(initial={'bloque':reservacion.horario.aula.bloque,
                                                                      'aula': reservacion.horario.aula,
                                                                      'persona': reservacion.horario.persona,
                                                                      'concepto': reservacion.horario.concepto,
                                                                      'periodo': reservacion.horario.materia.nivel.periodo,
                                                                      'carrera': reservacion.horario.materia.asignaturamalla.malla.carrera,
                                                                      'materia': reservacion.horario.materia,
                                                                      'inicio': reservacion.inicio.date(),
                                                                      'fin': reservacion.fin.date(),
                                                                      'horainicio': str(reservacion.comienza)[0:5],
                                                                      'horafin': str(reservacion.termina)[0:5],
                                                                      'dia': reservacion.dia})

                        if reservacion.horario.persona:
                            form.edit_per(reservacion.horario.persona.id)

                        if reservacion.horario.materia:
                            form.edit_mat(reservacion.horario.materia.id, reservacion.horario.materia.asignaturamalla.malla.carrera.id)
                    else:
                        form = HorariosAulasLabEditForm(initial={'bloque':reservacion.horario.aula.bloque,
                                                                  'aula': reservacion.horario.aula,
                                                                  'persona': reservacion.horario.persona,
                                                                  'concepto': reservacion.horario.concepto,
                                                                  'inicio': reservacion.inicio.date(),
                                                                  'fin': reservacion.fin.date(),
                                                                  'horainicio': str(reservacion.comienza)[0:5],
                                                                  'horafin': str(reservacion.termina)[0:5],
                                                                  'dia': reservacion.dia})
                        if reservacion.horario.persona:
                            form.edit_per(reservacion.horario.persona.id)

                    data['form'] = form
                    form.fields['periodo'].queryset = Periodo.objects.filter(status=True).order_by('-id')
                    return render(request, "adm_laboratorioscomputacion/editconfig.html", data)
                except Exception as ex:
                    pass

            elif action == 'editreservaciones':
                try:
                    data['title'] = u'Editar reservación de aulas'
                    data['horario'] = horario = HorariosAulasLaboratorios.objects.get(status=True, id=request.GET['id'])
                    data['detalle'] = horario.detallereservacionaulas_set.filter(status=True)
                    form = HorariosAulasLaboratoriosForm(initial={'bloque':horario.aula.bloque,
                                                             'aula': horario.aula,
                                                             'persona': horario.persona,
                                                             'concepto': horario.concepto,
                                                             'periodo': horario.materia.nivel.periodo if horario.materia else None,
                                                             'carrera': horario.materia.asignaturamalla.malla.carrera if horario.materia else None,
                                                             'materia': horario.materia if horario.materia else None,
                                                             'tienemateria': True if horario.materia else False,})

                    if horario.persona:
                        form.edit_per(horario.persona.id)

                    if horario.materia:
                        form.edit_mat(horario.materia.id, horario.materia.asignaturamalla.malla.carrera.id,horario.materia.asignaturamalla.nivelmalla.id)


                    data['form'] = form
                    return render(request, "adm_laboratorioscomputacion/edtireservaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdistribucion':
                try:
                    data['title'] = u'Editar distribución de personal'
                    data['distribucion'] = distribuido = DetalleDistribucionPersonal.objects.get(status=True, pk=request.GET['id'])

                    form = DistribucionPersonalAulasEditForm(initial={'bloque':distribuido.distribucion.bloque,
                                                                  'persona': distribuido.distribucion.encargado,
                                                                  'aula': distribuido.aula,
                                                                  'inicio': distribuido.inicio.date(),
                                                                  'fin': distribuido.fin.date(),
                                                                  'horainicio': str(distribuido.comienza)[0:5],
                                                                  'horafin': str(distribuido.termina)[0:5]})

                    data['form'] = form
                    return render(request, "adm_laboratorioscomputacion/editdistribucion.html", data)
                except Exception as ex:
                    pass

            elif action == 'searchPersona':
                try:
                    q = request.GET['q'].upper().strip()
                    profesores = Persona.objects.filter(perfilusuario__profesor__isnull=False).values_list('id', flat=True)
                    administrativos = Persona.objects.filter(perfilusuario__administrativo__isnull=False).values_list('id', flat=True)
                    idpersonasaptas = profesores.union(administrativos)
                    personasaptas = Persona.objects.filter(id__in=[idpersonasaptas])
                    ss = q.split()
                    if len(ss)>1:
                        ePersona = personasaptas.filter(Q(apellido1=ss[0]) | Q(apellido2=ss[1]) | Q(nombres__icontains=q))
                    else:
                        ePersona = personasaptas.filter(Q(apellido1__icontains=q) | Q(apellido2__icontains=q) | Q(nombres__icontains=q))
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.nombre_completo_inverso()} for x in ePersona]}
                    return JsonResponse(data)
                except Exception as ex:
                    data = {"result": "ok", "results": []}
                    return JsonResponse(data)

            elif action == 'segmento':
                try:
                    data['title'] = u'Horarios de Laboratorios'

                    if 'fecha' in request.GET:
                        nombremes = MESES_CHOICES[datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().month - 1][1]
                        weekday = DIAS_CHOICES[datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().isoweekday() - 1][1]

                        data['weekday'] = weekday + ', ' + str(datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().day) + ' de ' + nombremes + ' de ' + str(datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().year)
                        data['dia'] = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().isoweekday()
                        data['fecha'] = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date()
                    else:
                        nombremes = MESES_CHOICES[datetime.now().date().month - 1][1]
                        weekday = DIAS_CHOICES[datetime.now().date().isoweekday() - 1][1]

                        data['weekday'] = weekday + ', ' + str(datetime.now().date().day) + ' de ' + nombremes + ' de ' + str(datetime.now().date().year)

                        data['dia'] = datetime.now().date().isoweekday()
                        data['fecha'] = datetime.now().date()

                    if 'idbloque' in request.GET:
                        data['idbloque2'] = int(request.GET['idbloque'])

                    if 'idaula' in request.GET:
                        data['idaula2'] = int(request.GET['idaula'])

                    data['bloques'] = Bloque.objects.filter(status=True, tiene_lab=True)
                    # data['aulas'] = Aula.objects.filter(status=True, clasificacion=1).order_by('bloque__id')

                    data['aula'] = Aula.objects.get(status=True, pk= int(request.GET['idaula']))

                    return render(request, "adm_laboratorioscomputacion/segmento.html", data)
                except Exception as ex:
                    pass

            elif action == 'segmentobloque':
                try:
                    data['title'] = u'Horarios de Laboratorios'

                    if 'idblock' in request.GET:
                        data['idbloque2'] = int(request.GET['idblock'])
                        data['bloqueobj'] = Bloque.objects.get(status=True, pk=int(request.GET['idblock']))
                        data['aulasbloque'] = Aula.objects.filter(status=True, clasificacion=1, bloque_id=int(request.GET['idblock']))

                    if 'fecha' in request.GET:
                        nombremes = MESES_CHOICES[datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().month - 1][1]
                        weekday = DIAS_CHOICES[datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().isoweekday() - 1][1]

                        data['weekday'] = weekday + ', ' + str(datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().day) + ' de ' + nombremes + ' de ' + str(datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().year)
                        data['dia'] = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().isoweekday()
                        data['fecha'] = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date()
                    else:
                        nombremes = MESES_CHOICES[datetime.now().date().month - 1][1]
                        weekday = DIAS_CHOICES[datetime.now().date().isoweekday() - 1][1]

                        data['weekday'] = weekday + ', ' + str(datetime.now().date().day) + ' de ' + nombremes + ' de ' + str(datetime.now().date().year)

                        data['dia'] = datetime.now().date().isoweekday()
                        data['fecha'] = datetime.now().date()

                    # if 'idbloque' in request.GET:
                    #     data['idbloque2'] = int(request.GET['idbloque'])

                    # if 'idaula' in request.GET:
                    #     data['idaula2'] = int(request.GET['idaula'])

                    data['bloques'] = Bloque.objects.filter(status=True, tiene_lab=True)
                    # data['aulas'] = Aula.objects.filter(status=True, clasificacion=1).order_by('bloque__id')

                    # data['aula'] = Aula.objects.get(status=True, pk= int(request.GET['idaula']))

                    return render(request, "adm_laboratorioscomputacion/segmentobloque.html", data)
                except Exception as ex:
                    pass

            elif action == 'distribucionpersonal':
                try:
                    data['title'] = 'Distribución del Personal'
                    url_vars = ''
                    url_vars += '&action={}'.format(action)

                    distribuciones = DetalleDistribucionPersonal.objects.filter(status=True).order_by('-id')
                    paging = MiPaginador(distribuciones, 10)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['distribuciones'] = page.object_list
                    data['url_vars'] = url_vars
                    # data['modulos'] = GestionPermisos.objects.values_list('modulo_id', 'modulo__nombre', 'modulo__url').filter(status=True).distinct()
                    return render(request, "adm_laboratorioscomputacion/configuracionpersonal.html", data)
                except Exception as ex:
                   return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'adddistribucion':
                try:
                    data['title'] = u'Adicionar distribución de personal'
                    form = DistribucionPersonalAulasForm()
                    data['form'] = form
                    return render(request, "adm_laboratorioscomputacion/adddistribucion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addnovedad':
                try:
                    horarioreserva = HorariosAulasLaboratorios.objects.get(status=True, pk=int(request.GET['id']))
                    data['clasificacion'] = clasificacion = int(request.GET['clasi'])
                    form = NovedadAulaForm(initial={'horario':'Aula: '+ str(horarioreserva.aula.nombre) + ' - horario: ' + str(horarioreserva.comienza)[0:5] + ' a ' + str(horarioreserva.termina)[0:5] + ' - Reservado por: ' + str(horarioreserva.persona)})
                    data['form2'] = form
                    data['action'] = 'addnovedad'
                    data['id'] = horarioreserva.id
                    if clasificacion == 1:
                        form.fields['tiponovedad'].queryset = TipoNovedad.objects.filter(status=True).exclude(id=5).order_by('id')
                    elif clasificacion == 2:
                        form.fields['tiponovedad'].queryset = TipoNovedad.objects.filter(status=True).exclude(id=4).order_by('id')
                    template = get_template("adm_laboratorioscomputacion/modal/addnovedad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historialnovedad':
                try:
                    if 'id' in request.GET:
                        data['historialnovedades'] = DetalleUsoAula.objects.filter(horario=request.GET['id'], status=True).order_by('id')
                        template = get_template("adm_laboratorioscomputacion/modal/historialnovedad.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'armadillo':
                try:
                    data['title'] = u'HORARIOS'

                    if 'idp' in request.GET:
                        id = encrypt(request.GET['idp'])
                        pantalla = PantallaAula.objects.get(status=True,id=id)
                        aula_ids = pantalla.detallepantallaaula_set.values_list('aula__id',flat=True).filter(status=True)
                        aula = Aula.objects.filter(status=True, clasificacion=1, id__in=aula_ids).order_by('nombre')
                    else:
                        aula =  Aula.objects.filter(status=True, clasificacion=1).order_by('nombre')

                    if 'idblock' in request.GET:
                        data['idbloque2'] = int(request.GET['idblock'])
                        data['bloqueobj'] = Bloque.objects.get(status=True, pk=int(request.GET['idblock']))
                        data['aulasbloque'] = Aula.objects.filter(status=True, clasificacion=1, bloque_id=int(request.GET['idblock']))

                    # if 'fecha' in request.GET:
                    #     nombremes = MESES_CHOICES[datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().month - 1][1]
                    #     weekday = DIAS_CHOICES[datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().isoweekday() - 1][1]
                    #
                    #     data['weekday'] = weekday + ', ' + str(datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().day) + ' de ' + nombremes + ' de ' + str(datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().year)
                    #     data['dia'] = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date().isoweekday()
                    #     data['fecha'] = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date()
                    # else:
                    nombremes = MESES_CHOICES[datetime.now().date().month - 1][1]
                    weekday = DIAS_CHOICES[datetime.now().date().isoweekday() - 1][1]

                    data['weekday'] = weekday + ', ' + str(datetime.now().date().day) + ' de ' + nombremes + ' de ' + str(datetime.now().date().year)

                    data['dia'] = datetime.now().date().isoweekday()
                    data['fecha'] = datetime.now().date()

                    # if 'idbloque' in request.GET:
                    #     data['idbloque2'] = int(request.GET['idbloque'])

                    # if 'idaula' in request.GET:
                    #     data['idaula2'] = int(request.GET['idaula'])

                    # data['bloques'] = Bloque.objects.filter(status=True, tiene_lab=True)
                    aulaslab = Aula.objects.filter(status=True, clasificacion=1, bloque_id=8).order_by('nombre')

                    # for lab in aulaslab:
                    #     if HorariosAulasLaboratorios.objects.filter(status=True, aula_id=lab.id).exist():
                    #         a=0


                    data['aulas'] = aula

                    # data['aula'] = Aula.objects.get(status=True, pk= int(request.GET['idaula']))

                    return render(request, "adm_laboratorioscomputacion/armadillooficial.html", data)
                except Exception as ex:
                    pass

            elif action == 'detallereservacion':
                try:
                    id = encrypt(request.GET['id'])
                    if not HorariosAulasLaboratorios.objects.filter(id=int(id),status=True).exists():
                        return JsonResponse({'result':False,'message':u'No se encuentra el registro, actualice la página.'})
                    data['horario'] = horario = HorariosAulasLaboratorios.objects.get(id=int(id),status=True)
                    data['detalle'] = detalle = horario.detallereservacionaulas_set.filter(status=True)
                    template = get_template("adm_laboratorioscomputacion/modal/detallereservacion.html")
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result':False,'message':'Ocurrio un error!. Detalle: %s'%ex.__str__()})

            elif action == 'configuracionaulas':
                try:
                    url_vars = '&action={}'.format(action)
                    data['title'] = u'Configuración de aulas'
                    pantalla = PantallaAula.objects.filter(status=True).order_by('-id')
                    paging = MiPaginador(pantalla, 10)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['pantalla'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_laboratorioscomputacion/viewconfiguracionaula.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpantallaaula':
                try:
                    form = PantallaAulaForm()
                    bloque =  persona.distribucionpersonallaboratorio_set.filter(status=True).values_list('bloque',flat=True)
                    form.fields['aula'].queryset = Aula.objects.filter(status=True,bloque__in = bloque)
                    data['form'] = form
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'message': 'Ocurrio un error!. Detalle: %s' % ex.__str__()})

            elif action == 'editpantallaaula':
                try:
                    id = encrypt(request.GET['id'])
                    if not PantallaAula.objects.values('id').filter(id=id,status=True):
                        raise NameError(u'No existe el registro.')
                    filtro = PantallaAula.objects.get(id=id,status=True)
                    form = PantallaAulaForm(initial={
                        'descripcion': filtro.descripcion,
                        'aula': filtro.detallepantallaaula_set.values_list('aula__id',flat=True).filter(status=True)
                    })
                    data['filtro'] = filtro
                    data['form'] = form
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'message': 'Ocurrio un error!. Detalle: %s' % ex.__str__()})

            elif action == 'cierrereservacion':
                try:
                    data['title'] = u'Gestión de cierres'
                    url_vars ='&action=cierrereservacion'
                    # bloque_search,aula_search,docente_search, dia_search = request.GET.get('bloque'), request.GET.get('aula'),request.GET.get('s'),request.GET.get('diasa')
                    bloque_search,aula_search,docente_search = request.GET.get('bloque'), request.GET.get('aula'),request.GET.get('s')
                    filtro = Q(status=True)
                    filtro_aulas = Q(status=True)

                    if DistribucionPersonalLaboratorio.objects.filter(status=True,encargado=persona).order_by('-id').exists():
                        bloque = DistribucionPersonalLaboratorio.objects.filter(status=True,encargado=persona).order_by('-id').first()
                        aulas = bloque.bloque.aula_set.values_list('id',flat=True).filter(status=True).distinct()
                    else:
                        messages.warning(request,"No tiene aulas asignadas")
                        return HttpResponseRedirect('/adm_laboratorioscomputacion')

                    if docente_search:
                        ss = docente_search.split(" ")
                        if len(ss) > 1:
                            filtro = filtro & \
                                     Q(horario__persona__nombres__icontains = docente_search) | \
                                     Q(horario__persona__apellido1=ss[0]) | \
                                     Q(horario__persona__apellido2=ss[1]) | \
                                     Q(horario__persona__cedula=ss[0]) | \
                                    Q(horario__materia__alias = docente_search)
                        else:
                            filtro = filtro & \
                                     Q(horario__persona__nombres__icontains = docente_search) | \
                                     Q(horario__persona__apellido1=docente_search) | \
                                     Q(horario__persona__apellido2=docente_search) | \
                                     Q(horario__persona__cedula=docente_search) | \
                                    Q(horario__materia__alias = docente_search)
                        url_vars +=f'&s={docente_search}'
                        data['s'] = docente_search
                    if aula_search:
                        if int(aula_search) > 0:
                            filtro = filtro & Q(horario__aula__id = aula_search)
                            data['aula'] = int(aula_search)
                            url_vars +='&aula='+aula_search
                    if bloque_search:
                        if int(bloque_search) > 0:
                            filtro = filtro & Q(horario__aula__bloque__id=bloque_search)
                            filtro_aulas = filtro_aulas & Q(bloque__id=bloque_search)
                            data['bloque'] = int(bloque_search)
                            url_vars += '&bloque=' + bloque_search

                    # if dia_search:
                    #     if len(dia_search)>0:
                    #         filtro = filtro & Q(dia = dia_search )
                    #         data['diasa'] = int(dia_search)
                    #         url_vars +=f'&diasa={dia_search}'

                    h = str(datetime.now().time())
                    horaactual = datetime.strptime(h[0:8], '%H:%M:%S').time()
                    fecha = datetime.now().date()
                    dianolaborable = CronogromaDiaNoLaborable.objects.filter(Q(Q(ffin__gte=fecha,
                                                                             fini__lte=fecha)|Q(ffin__gte=fecha,
                                                                             fini__lte=fecha)),status=True, activo =True).order_by('-id').first()
                    # detalle1 = DetalleReservacionAulas.objects.filter(status=True, horario__aula_id__in=aulas,
                    #     ).filter(filtro).exclude(dia=fecha.isoweekday()).order_by('dia', 'comienza').annotate(
                    #     qs_order=models.Value(2, models.IntegerField())
                    # )  # inicio__lte=fecha,fin__gte=fecha,comienza__lte=horaactual,termina__gte=horaactual
                    detalle2 = DetalleReservacionAulas.objects.filter(
                        status=True, horario__aula_id__in=aulas, dia=fecha.isoweekday(),inicio__date__lte=fecha,fin__date__gte=fecha)\
                        .filter(filtro)\
                        .order_by('oculto','dia', 'comienza')\
                        .annotate(qs_order=models.Value(1, models.IntegerField()))
                    if dianolaborable and bloque.bloque.id in DistribucionPersonalLaboratorio.objects.values_list('bloque_id',flat=True).filter(status=True).filter(Q(Q(encargado__usuario__id=dianolaborable.usuario_creacion.id)|Q(encargado__usuario__id=dianolaborable.usuario_modificacion.id if dianolaborable.usuario_modificacion else None ))):
                        # filtrodianolabo = Q(inicio__date__range = (dianolaborable.fini,dianolaborable.ffin))
                        filtrodianolabo = Q(inactivo=True)
                        detalle2 = detalle2.exclude(filtrodianolabo)
                    # detalle = detalle2.union(detalle1).order_by('qs_order','dia','comienza')
                    data['tiponovedad'] = TipoNovedad.objects.filter(status=True).order_by('id','descripcion')
                    data['bloques'] = bloques = Bloque.objects.filter(status=True, tiene_lab=True,id=bloque.bloque.id)
                    data['aulas'] = aulas_sea = Aula.objects.filter(status=True,bloque__tiene_lab=True,bloque_id=bloque.bloque.id).filter(filtro_aulas)
                    data['dias'] = DIAS_CHOICES
                    data['registros'] = [ar for ar in detalle2.filter(oculto=True).values_list('id',flat=True)]

                    paging = MiPaginador(detalle2, 10)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_laboratorioscomputacion/cierrereservacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewregistros':
                try:
                    data['title'] = u"Historial de ingreso-salida"
                    if not 'id' in request.GET:
                        messages.warning(request,"No existe el registro")
                        raise NameError()
                    id = encrypt(request.GET['id'])
                    if not DetalleReservacionAulas.objects.values('id').filter(status=True,id=id).exists():
                        messages.warning(request, "No existe el registro")
                        raise NameError()
                    detallereser = DetalleReservacionAulas.objects.get(status=True,id= id)
                    url_vars = f"&action={action}"
                    lista = detallereser.detalleusoaula_set.filter(status=True)
                    data['listado'] = lista

                    return render(request,"adm_laboratorioscomputacion/viewingresocierre.html",data)
                except Exception as ex:
                    pass

            elif action == 'tiponovedadconf':
                try:
                    data['title'] = u"Tipo de novedad"
                    filtro = Q(status=True)
                    url_vars = f'&action={action}'
                    tipo = TipoNovedad.objects.filter(status=True).order_by('-id')
                    if 's' in request.GET:
                        data['s'] = search = request.GET['s']
                        filtro = filtro & Q(descripcion__icontains=search)
                        url_vars +='s='+search
                    tipo = tipo.filter(filtro).order_by('-id')
                    paging = MiPaginador(tipo, 15)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request,"adm_laboratorioscomputacion/viewtiponovedad.html",data)

                except Exception as ex:
                    pass

            elif action == 'addtiponovedad':
                try:
                    data['title'] = u'Agregar tipo novedad'
                    form = TipoNovedadForm()
                    data['form'] = form
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result':False,'mensaje':u"Ocurrio un error: %s" % (ex.__str__())})

            elif action == 'edittiponovedad':
                try:
                    id = encrypt(request.GET['id'])
                    if not TipoNovedad.objects.filter(status=True,id=id).exists():
                        raise NameError('No existe el registro.')
                    data['filtro'] = filtro = TipoNovedad.objects.get(status=True,id=id)
                    data['title'] = u'Agregar tipo novedad'
                    form = TipoNovedadForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result':False,'mensaje':u"Ocurrio un error: %s" % (ex.__str__())})

            elif action == 'excel_registrohorarios':
                try:
                    data['title'] = u'Registro de horarios'
                    form = ReportesFechas()
                    data['form'] = form
                    form.reservas_horarios()
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result':False,'mensaje':u"Ocurrio un error: %s" % (ex.__str__())})

            elif action == 'excel_revisionsalas':
                try:
                    data['title'] = u'Registro de horarios'
                    form = ReportesFechas()
                    form.fields['tiponovedad'].initial = TipoNovedad.objects.filter(status=True).values_list('id',flat=True)
                    data['form'] = form
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result':False,'mensaje':u"Ocurrio un error: %s" % (ex.__str__())})


            elif action == 'editingresosalida':
                try:
                    id = encrypt(request.GET['id'])
                    if not DetalleUsoAula.objects.filter(status=True,id=id).exists():
                        raise NameError('No existe el registro.')
                    data['filtro'] = filtro = DetalleUsoAula.objects.get(status=True,id=id)
                    data['title'] = u'Editar ingreso-salida'
                    form = CierreIngresoForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result':False,'mensaje':u"Ocurrio un error: %s" % (ex.__str__())})

            elif action == 'viewcronograma':
                try:

                    if DistribucionPersonalLaboratorio.objects.filter(status=True,encargado=persona).order_by('-id').exists():
                        bloque = DistribucionPersonalLaboratorio.objects.filter(status=True,encargado=persona).order_by('-id').first()
                        usuario_id = DistribucionPersonalLaboratorio.objects.values_list("encargado__usuario_id", flat=True).filter(status=True,bloque=bloque.bloque)
                    else:
                        messages.warning(request,"No tiene aulas asignadas")
                        return HttpResponseRedirect('/adm_laboratorioscomputacion')
                    data['title'] = u'Cronograma'
                    url_vars,filtro = '',Q(Q(status=True)&Q(usuario_creacion__in=usuario_id))
                    query = CronogromaDiaNoLaborable.objects.filter(filtro)
                    paging = MiPaginador(query, 15)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request,'adm_laboratorioscomputacion/viewcronograma.html',data)
                except Exception as ex:
                    pass

            elif action == 'addcronograma':
                try:
                    data['title'] = u'Agregar día no laborable'
                    form = CronogramaDiaNoLaborableForm()
                    data['form'] = form
                    data['action'] = 'addcronograma'
                    # template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    # return JsonResponse({'result': True, 'data': template.render(data)})
                    return render(request,"adm_laboratorioscomputacion/formdianolaboral.html",data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'message': 'Ocurrio un error!. Detalle: %s' % ex.__str__()})

            elif action == 'editcronograma':
                try:
                    data['title'] = u'Editar día no laborable'
                    id = encrypt(request.GET['id'])
                    filtro = CronogromaDiaNoLaborable.objects.get(status=True,id=id)
                    form = CronogramaDiaNoLaborableForm(initial=model_to_dict(filtro))
                    data['det'] = det = DetalleReservacionAulas.objects.filter(status=True,inicio__date__range = (filtro.fini,filtro.ffin),fin__date__range = (filtro.fini,filtro.ffin))
                    data['form'] = form
                    data['filtro'] = filtro
                    data['action'] = 'editcronograma'
                    return render(request,"adm_laboratorioscomputacion/formdianolaboral.html",data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'message': 'Ocurrio un error!. Detalle: %s' % ex.__str__()})

            elif action == 'verificarreservaciones':
                try:
                    bloque = None
                    aulas = None
                    if DistribucionPersonalLaboratorio.objects.filter(status=True,encargado=persona).order_by('-id').exists():
                        bloque = DistribucionPersonalLaboratorio.objects.filter(status=True,encargado=persona).order_by('-id').first()
                        aulas = bloque.bloque.aula_set.values_list('id',flat=True).filter(status=True).distinct()
                    else:
                        messages.warning(request,"No tiene aulas asignadas")
                        return HttpResponseRedirect('/adm_laboratorioscomputacion')
                    fini, ffin = request.GET.get('fini',None),request.GET.get('ffin',None)
                    lista = []
                    if fini:
                        fini = datetime.strptime(fini, '%Y-%m-%d').date()
                    if ffin:
                        ffin = datetime.strptime(ffin, '%Y-%m-%d').date()
                    reservaciones = DetalleReservacionAulas.objects.filter(Q( Q(horario__aula__id__in=aulas) &((Q(inicio__date__range=(fini, ffin)) | (
                            Q(fin__date__range=(fini, ffin))))
                               | Q(Q(inicio__date__lte=fini) & Q(fin__date__gte=ffin)))),status=True).exclude(examen=True).order_by('-inicio')
                    if reservaciones:
                        for res in reservaciones:
                            lista.append([encrypt(res.id),res.inicio.date().strftime('%d/%m/%Y'),res.fin.date().strftime('%d/%m/%Y'),res.get_dia_display(),str(res.comienza),str(res.termina),'true' if type(res.inactivo) == type(None) or res.inactivo else 'false', f'{res.horario.aula.nombre} - {res.horario.aula.bloque}',res.horario.persona.__str__()])
                    return JsonResponse({'result': True, 'data': lista})
                except Exception as ex:
                    return JsonResponse({'result': False, 'message': 'Ocurrio un error!. Detalle: %s' % ex.__str__()})

            elif action == 'validarhorariosreserv':
                try:
                    filtrodianolabo = Q(status=False)
                    fecha = datetime.now().date()
                    fecha_fin= datetime.now().strptime(request.GET['fin'],"%Y-%m-%d").date()
                    fecha_inicio= datetime.now().strptime(request.GET['inicio'],"%Y-%m-%d").date()
                    aula_id = request.GET['aula_id']
                    dianolaborable = CronogromaDiaNoLaborable.objects.filter(Q(Q(ffin__gte=fecha_inicio,
                                                                             fini__lte=fecha_inicio)|Q(ffin__gte=fecha_fin,
                                                                             fini__lte=fecha_fin)),status=True, activo=True).order_by(
                        '-id').first()

                    fechainicio = datetime.strptime(request.GET['inicio'], '%Y-%m-%d').date()
                    fechafin = datetime.strptime(request.GET['fin'], '%Y-%m-%d').date()
                    horaini = datetime.strptime(request.GET['horaini'], '%H:%M').time()
                    horafin = datetime.strptime(request.GET['horafin'], '%H:%M').time()
                    dia = int(request.GET['dia'])
                    if dianolaborable:
                        # filtrodianolabo = Q(inicio__date__range=(dianolaborable.fini, dianolaborable.ffin))
                        filtrodianolabo = Q(inactivo=True)

                    if DetalleReservacionAulas.objects.filter(
                            Q(dia=dia, horario__aula__id=aula_id, status=True)
                            & ((Q(inicio__date__range=(fechainicio, fechafin)) | (
                            Q(fin__date__range=(fechainicio, fechafin))))
                               | Q(Q(inicio__date__lte=fechainicio) & Q(fin__date__gte=fechafin)))
                            & ((Q(comienza__range=(horaini, horafin)) | Q(termina__range=(horaini, horafin))) |
                               Q(Q(comienza__lte=horaini) & Q(termina__gte=horafin)))) \
                            .exclude(filtrodianolabo).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'result': False,
                                             "mensaje": f'La reservación tiene conflictos de horarios. F. Inicia: {fechainicio} - F. Fin: {fechafin} - H. Inicia: {horaini} - H. Fin: {horafin} - Dia: {DIAS_CHOICES[dia - 1][1]}'},
                                            safe=False)

                    res_js = {"result": True}
                except Exception as ex:
                    line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(line_error)
                    res_js = {"result":False,"mensaje":"Ocurrio un error!. Detalle: %s"% ex.__str__(),"line_erro":line_error}
                return JsonResponse(res_js)

            elif action == 'viewinventario':
                try:
                    url_vars, filtro,estado,search,fdesde,fhasta = 'action=viewinventario', Q(status=True),request.GET.get('estadoscomp',0),request.GET.get('s',''),request.GET.get('fechadesde',None),request.GET.get('fechahasta',None)
                    data['title'] = u'Inventario'
                    if int(estado) != 0:
                        data['estadoscomp'] = int(estado)
                        filtro = filtro & Q(estado=estado)
                        url_vars +='&estadoscomp='+estado
                    if search != '':
                        data['s'] = search
                        filtro = filtro & Q(Q(activo__codigointerno=search)|
                                            Q(activo__codigogobierno=search)|
                                            Q(activo__observacion__icontains=search)|
                                            Q(observacion__icontains=search))
                        url_vars += '&s='+ search
                    if fdesde:
                        fecha_desde = datetime.now().strptime(fdesde,"%Y-%m-%d").date()
                        data['fechadesde'] = fdesde
                        filtro = filtro & Q(fecha_constata__gte=fecha_desde)
                        url_vars += '&fechadesde=' + fdesde
                    if fhasta:
                        fecha_hasta = datetime.now().strptime(fhasta,"%Y-%m-%d").date()
                        data['fechahasta'] = fhasta
                        filtro = filtro & Q(fecha_constata__lte=fecha_hasta)
                        url_vars += '&fechahasta=' + fhasta

                    query = ConstatacionFisicaLaboratorios.objects.filter(filtro)
                    paging = MiPaginador(query, 15)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    data['estados'] = ESTADO_CONSTATACION
                    if 'report_excel' in request.GET:
                        fehca_actual = datetime.now().strftime("%d_%m_%Y_%H_%M")
                        file_name = f'constatacion_fisica_{fehca_actual}'
                        __author__ = 'Unemi'

                        output = io.BytesIO()
                        workbook = xlsxwriter.Workbook(output)
                        ws = workbook.add_worksheet('resultados')
                        fuentecabecera = workbook.add_format({
                            'align': 'center',
                            'bg_color': 'silver',
                            'border': 1,
                            'bold': 1
                        })
                        formatoceldacenter = workbook.add_format({
                            'border': 1,
                            'valign': 'vcenter',
                            'align': 'center'})

                        columnas = [
                            ('Activo', 80),
                            ('Cod. interno', 20),
                            ('Cod. gobierno', 20),
                            ('Aula', 40),
                            ('Estado', 30),
                            ('Fecha', 20),
                            ('Hora', 20),
                            ('Responsable', 60),
                            ('Cedula', 20)
                        ]

                        row_num, numcolum = 0, 0

                        for cl in range(len(columnas)):
                            ws.write(row_num, cl, columnas[cl][0], fuentecabecera)
                            ws.set_column(cl, cl, columnas[cl][1])
                        row_num = 1

                        for consta in query:
                            ws.write(row_num,0,consta.activo.__str__() if consta.activo else '',formatoceldacenter)
                            ws.write(row_num,1,consta.activo.codigointerno if consta.activo else '',formatoceldacenter)
                            ws.write(row_num,2,consta.activo.codigogobierno if consta.activo else '',formatoceldacenter)
                            ws.write(row_num,3,consta.aula.__str__() if consta.aula else '',formatoceldacenter)
                            ws.write(row_num,4,consta.get_estado_display(),formatoceldacenter)
                            ws.write(row_num,5,str(consta.fecha_constata) if consta.fecha_constata else '-',formatoceldacenter)
                            ws.write(row_num,6,str(consta.hora_constata)if consta.hora_constata else '',formatoceldacenter)
                            ws.write(row_num,7,consta.activo.responsable.__str__() if consta.activo.responsable else '',formatoceldacenter)
                            ws.write(row_num,8,consta.activo.responsable.cedula if consta.activo.responsable else '',formatoceldacenter)
                            row_num +=1

                        workbook.close()
                        output.seek(0)
                        response = HttpResponse(output,
                                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        response['Content-Disposition'] = 'attachment; filename=%s' % file_name
                        return response

                    return render(request,"adm_laboratorioscomputacion/viewinventario.html",data)
                except Exception as ex:
                    line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print("Detalle: %s -%s" % (ex.__str__(),line_error))

            elif action == 'addinventario':
                try:
                    form = ConstatacionFisicaLaboratoriosForm()
                    data['form'] = form
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    res_js = {"result": True,'data':template.render(data)}
                except Exception as ex:
                    line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(line_error)
                    res_js = {"result": False, "mensaje": "Ocurrio un error!. Detalle: %s" % ex.__str__(),"line_erro": line_error}
                return JsonResponse(res_js)

            elif action == 'editinventario':
                try:
                    id = int(encrypt(request.GET['id']))
                    filtro = ConstatacionFisicaLaboratorios.objects.get(id=id,status=True)
                    form = ConstatacionFisicaLaboratoriosForm(initial=model_to_dict(filtro))
                    form.fields['hora_constata'].initial = filtro.hora_constata.strftime("%H:%M")
                    data['filtro'] = filtro
                    data['form'] = form
                    template = get_template("adm_laboratorioscomputacion/modal/formmodal.html")
                    res_js = {"result": True,'data':template.render(data)}
                except Exception as ex:
                    line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(line_error)
                    res_js = {"result": False, "mensaje": "Ocurrio un error!. Detalle: %s" % ex.__str__(),"line_erro": line_error}
                return JsonResponse(res_js)

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Horarios de Laboratorios'

                url_vars = ''

                data['bloques'] = Bloque.objects.filter(status=True, tiene_lab=True)
                # data['aulas'] = Aula.objects.filter(status=True, clasificacion=1).order_by('bloque__id')


                data['url_vars'] = url_vars
                return render(request, "adm_laboratorioscomputacion/view.html", data)
            except Exception as ex:
                pass