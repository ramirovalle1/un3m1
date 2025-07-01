# -*- coding: UTF-8 -*-
import json
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.db.models import Q
from django.template.context import Context
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.forms import PermisoInstitucionalForm, PermisoInstitucionalDetalleForm, PemisoInstitucionalArchivoForm
from sagest.models import HojaRuta, PermisoInstitucional, DistributivoPersona, TipoPermiso, null_to_numeric, \
    TipoPermisoDetalle, PermisoInstitucionalDetalle, IngresoPersonal, KardexVacacionesDetalle, \
    HistorialJornadaTrabajador, DetalleJornada, CategoriaTipoPermiso, PermisoAprobacion
from settings import EMAIL_DOMAIN, PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, generar_nombre, convertir_fecha_invertida, variable_valor, \
    notificacion
from sga.models import miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


def rango_anios():
    if HojaRuta.objects.exists():
        inicio = datetime.now().year
        fin = HojaRuta.objects.order_by('fecha')[0].fecha.year
        return range(inicio, fin - 1, -1)
    return [datetime.now().date().year]


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'adicionar':
            try:
                f = PermisoInstitucionalForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            if not ext == '.PDF':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("Solicitud", newfile._name)
                else:
                    if TipoPermisoDetalle.objects.get(pk=int(request.POST['tipopermisodetalle'])).perdirarchivo:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})
                    if 'categoriapermiso' in request.POST:
                        if request.POST['categoriapermiso'] != '':
                            if CategoriaTipoPermiso.objects.filter(pk=request.POST['categoriapermiso']).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    cumple=True
                    tipopermiso=f.cleaned_data['tipopermiso']
                    fecha = datetime.now().date()
                    datos = json.loads(request.POST['lista_items1'])
                    tipopermisodetalle = f.cleaned_data['tipopermisodetalle']
                    denominacionpuesto = f.cleaned_data['denominacionpuesto']
                    categoriatipopermiso = f.cleaned_data['categoriapermiso']
                    # regimen = DistributivoPersona.objects.filter(persona=persona,denominacionpuesto=denominacionpuesto.denominacionpuesto,estadopuesto_id=1)[0].regimenlaboral_id
                    lista = []
                    if not datos:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar la duración del permiso."})
                    for d in datos:
                        fechainicio = convertir_fecha(d['fechainicio'])
                        horainicio = int(d['horainicio'].split(':')[0])
                        minutoinicio = int(d['horainicio'].split(':')[1])
                        fechafin = convertir_fecha(d['fechafin'])
                        horafin = int(d['horafin'].split(':')[0])
                        minutofin = int(d['horafin'].split(':')[1])
                        resultado = valida_este_en_fecha(tipopermisodetalle,fechainicio)
                        if tipopermiso.id != 27 and tipopermiso.id != 24:
                            resultado_en_dia = valida_este_en_dias(tipopermisodetalle, fechainicio, fechafin)
                            if not resultado[0] and not resultado_en_dia[0]:
                                return JsonResponse({"result": "bad", "mensaje": resultado[1] +" Y "+ resultado_en_dia[1]})
                            else:
                                if not resultado[0]:
                                    return JsonResponse({"result": "bad", "mensaje": resultado[1]})
                                if not resultado_en_dia[0]:
                                    return JsonResponse({"result": "bad", "mensaje": resultado_en_dia[1]})
                        elif tipopermiso.id == 27 or tipopermiso.id == 24 or tipopermiso.id==12:
                            cumple = verificar_si_tiene_saldo_vacaciones_1(tipopermiso.id, d['horainicio'],
                                                                           d['horafin'], persona, fechainicio, fechafin,
                                                                           denominacionpuesto.id)
                        if not cumple :
                            return JsonResponse({"result": "bad", "mensaje": "NO TIENE SALDO DE VACACIONES."})

                        lista.append([datetime(fechainicio.year, fechainicio.month, fechainicio.day, horainicio, minutoinicio), datetime(fechafin.year, fechafin.month, fechafin.day, horafin, minutofin)])
                    p = 1

                    def hora_dia(hr, mi):
                        now = datetime.now()
                        return now.replace(hour=hr, minute=mi, second=0, microsecond=0)

                    for elemento in lista:
                        otros = lista
                        otros.remove(elemento)
                        for otro in otros:
                            if otro[0] <= elemento[0] <= otro[1]:
                                if hora_dia(otro[0].hour, otro[0].minute) <= hora_dia(elemento[0].hour, elemento[0].minute) <= hora_dia(otro[1].hour, otro[1].minute):
                                    return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                            if otro[0] <= elemento[1] <= otro[1]:
                                if hora_dia(otro[0].hour, otro[0].minute) <= hora_dia(elemento[1].hour, elemento[1].minute) <= hora_dia(otro[1].hour, otro[1].minute):
                                    return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                        p += 1
                    secu = null_to_numeric(PermisoInstitucional.objects.filter(solicita=persona, fechasolicitud__year=fecha.year).aggregate(secu=Max("secuencia"))['secu'])
                    secuencia = secu + 1
                    if not persona.mis_plantillas_actuales().filter(denominacionpuesto=denominacionpuesto.denominacionpuesto).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error no existe la unidad organica."})
                    unidadorganica = persona.mis_plantillas_actuales().filter(denominacionpuesto=denominacionpuesto.denominacionpuesto)[0].unidadorganica
                    if not unidadorganica.responsable:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"No existe un responsable del departamento, consulte con talento humano."})

                    if 'permisofamilia' in request.POST:
                        permisofamilia = f.cleaned_data['permisofamilia']
                    else:
                        permisofamilia = None
                    permiso = PermisoInstitucional(fechasolicitud=fecha,
                                                   solicita=persona,
                                                   secuencia=secuencia,
                                                   permisofamilia=permisofamilia,
                                                   tiposolicitud=f.cleaned_data['tiposolicitud'],
                                                   tipopermiso=f.cleaned_data['tipopermiso'],
                                                   tipopermisodetalle=f.cleaned_data['tipopermisodetalle'],
                                                   descuentovacaciones=False if not tipopermisodetalle else tipopermisodetalle.descuentovacaciones,
                                                   motivo=f.cleaned_data['motivo'],
                                                   estadosolicitud=1,
                                                   denominacionpuesto=denominacionpuesto.denominacionpuesto,
                                                   regimenlaboral=denominacionpuesto.regimenlaboral,
                                                   unidadorganica=unidadorganica,
                                                   casasalud=f.cleaned_data['casasalud'],
                                                   categoriatipopermiso = f.cleaned_data['categoriapermiso'])
                    permiso.save(request)
                    if newfile:
                        permiso.archivo = newfile
                        permiso.save(request)
                    for d in datos:
                        detalleingprod = PermisoInstitucionalDetalle(permisoinstitucional=permiso,
                                                                     fechainicio=convertir_fecha(d['fechainicio']),
                                                                     fechafin=convertir_fecha(d['fechafin']),
                                                                     horainicio=d['horainicio'],
                                                                     horafin=d['horafin'])
                        detalleingprod.save(request)
                    send_html_mail("Solicitud de permiso de %s" % permiso.solicita.nombre_completo_minus(), "emails/permisosolicita.html", {'sistema': request.session['nombresistema'],'permiso':permiso,'detalle':detalleingprod, 'codificacion': permiso.codificacion(), 'responsable': permiso.unidadorganica.responsable, 'solicita': permiso.solicita, 't': miinstitucion()}, permiso.unidadorganica.responsable.lista_emails_interno(), [], cuenta=CUENTAS_CORREOS[1][1])
                    log(u'Adiciono nueva solicitud de permiso: %s' % permiso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                f = PermisoInstitucionalForm(request.POST, request.FILES)
                newfile = None
                permiso = PermisoInstitucional.objects.get(pk=int(request.POST['id']))
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            if not ext == '.PDF':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("Solicitud", newfile._name)
                else:
                    detallepermiso = TipoPermisoDetalle.objects.get(pk=int(request.POST['tipopermisodetalle']))
                    if detallepermiso.perdirarchivo and not detallepermiso.id == permiso.tipopermisodetalle.id:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})
                    if 'categoriapermiso' in request.POST:
                        if not permiso.archivo:
                            if request.POST['categoriapermiso'] != '':
                                if CategoriaTipoPermiso.objects.filter(pk=int(request.POST['categoriapermiso'])).exists():
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    tipopermisodetalle = f.cleaned_data['tipopermisodetalle']
                    denominacionpuesto = f.cleaned_data['denominacionpuesto']
                    unidadorganica = persona.mis_plantillas_actuales().filter(denominacionpuesto=denominacionpuesto.denominacionpuesto)[0].unidadorganica
                    lista = []
                    listaeditar = []
                    if not datos:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un rango de tiempo."})
                    for d in datos:
                        fechainicio = convertir_fecha(d['fechainicio'])
                        horainicio = int(d['horainicio'].split(':')[0])
                        minutoinicio = int(d['horainicio'].split(':')[1])
                        fechafin = convertir_fecha(d['fechafin'])
                        horafin = int(d['horafin'].split(':')[0])
                        minutofin = int(d['horafin'].split(':')[1])
                        ne = d['ne']
                        if not ne[:1] == 'e':
                            resultado = valida_este_en_fecha(tipopermisodetalle, fechainicio, permiso.fechasolicitud)
                            if permiso.tipopermiso_id != 12 and permiso.tipopermiso_id != 27 and permiso.tipopermiso_id != 24:
                                resultado_en_dia = valida_este_en_dias(tipopermisodetalle, fechainicio, fechafin)
                                if not resultado[0] and not resultado_en_dia[0]:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": resultado[1] + " Y " + resultado_en_dia[1]})
                                else:
                                    if not resultado[0]:
                                        return JsonResponse({"result": "bad", "mensaje": resultado[1]})
                                    if not resultado_en_dia[0]:
                                        return JsonResponse({"result": "bad", "mensaje": resultado_en_dia[1]})
                        else:
                            listaeditar.append(int(ne[1:ne.__len__()]))
                        lista.append([datetime(fechainicio.year, fechainicio.month, fechainicio.day, horainicio, minutoinicio),
                                      datetime(fechafin.year, fechafin.month, fechafin.day, horafin, minutofin)])
                    p = 1

                    def hora_dia(hr, mi):
                        now = datetime.now()
                        return now.replace(hour=hr, minute=mi, second=0, microsecond=0)

                    for elemento in lista:
                        otros = lista
                        otros.remove(elemento)
                        for otro in otros:
                            if otro[0] <= elemento[0] <= otro[1]:
                                if hora_dia(otro[0].hour, otro[0].minute) <= hora_dia(elemento[0].hour,
                                                                                      elemento[0].minute) <= hora_dia(
                                        otro[1].hour, otro[1].minute):
                                    return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                            if otro[0] <= elemento[1] <= otro[1]:
                                if hora_dia(otro[0].hour, otro[0].minute) <= hora_dia(elemento[1].hour,
                                                                                      elemento[1].minute) <= hora_dia(
                                        otro[1].hour, otro[1].minute):
                                    return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                        p += 1
                    if not persona.mis_plantillas_actuales().filter(denominacionpuesto=denominacionpuesto.denominacionpuesto).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error no existe la unidad organica."})
                    if 'permisofamilia' in request.POST:
                        permisofamilia = f.cleaned_data['permisofamilia']
                    else:
                        permisofamilia = None

                    if permiso.estadosolicitud==6:
                        destinatario = permiso.permisoaprobacion_set.filter(estadosolicitud=4, status=True).last().aprueba
                        notificacion('Permiso institucional', ('Se ha modificado el permiso: %s ' % permiso), destinatario,
                                     None, ('/th_aprobarpermiso_th?s=%s' % permiso.solicita.identificacion()), permiso.pk,
                                     1, 'sga-sagest', PermisoInstitucional, request)
                    unidadorganica = persona.mis_plantillas_actuales().filter(denominacionpuesto=denominacionpuesto.denominacionpuesto)[0].unidadorganica
                    permiso.tiposolicitud = f.cleaned_data['tiposolicitud']
                    permiso.tipopermiso = f.cleaned_data['tipopermiso']
                    permiso.tipopermisodetalle = f.cleaned_data['tipopermisodetalle']
                    permiso.descuentovacaciones = False if not tipopermisodetalle else tipopermisodetalle.descuentovacaciones
                    permiso.motivo = f.cleaned_data['motivo']
                    permiso.estadosolicitud = 1
                    permiso.denominacionpuesto = denominacionpuesto.denominacionpuesto
                    permiso.unidadorganica = unidadorganica
                    permiso.permisofamilia = permisofamilia
                    permiso.casasalud = f.cleaned_data['casasalud']
                    permiso.categoriatipopermiso = f.cleaned_data['categoriapermiso']
                    permiso.save(request)
                    if newfile:
                        permiso.archivo = newfile
                        permiso.save(request)
                    permiso.permisoinstitucionaldetalle_set.all().exclude(pk__in=listaeditar).delete()
                    for d in datos:
                        ne = d['ne']
                        if ne[:1]=='n':
                            detalleingprod = PermisoInstitucionalDetalle(permisoinstitucional=permiso,
                                                                         fechainicio=convertir_fecha(d['fechainicio']),
                                                                         fechafin=convertir_fecha(d['fechafin']),
                                                                         horainicio=d['horainicio'],
                                                                         horafin=d['horafin'])
                        else:
                            detalleingprod = PermisoInstitucionalDetalle.objects.get(pk=int(ne[1:ne.__len__()]))
                            detalleingprod.horainicio = d['horainicio']
                            detalleingprod.horafin = d['horafin']
                        detalleingprod.save(request)


                    log(u'Modifico solicitud de permiso: %s' % permiso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'del_permiso':
            try:
                permiso = PermisoInstitucional.objects.get(pk=request.POST['id'])
                permiso.permisoinstitucionaldetalle_set.all().delete()
                permiso.delete()
                log(u'Elimino solicitud de permiso: %s' % permiso, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al elminar los datos."})

        elif action == 'permisofamilia':
            try:
                detalle = TipoPermisoDetalle.objects.get(pk=int(request.POST['id']))
                permisosfamilia = detalle.tipopermisodetallefamilia_set.filter(status=True)
                pedirarchivo = detalle.perdirarchivo
                if 'ids' in request.POST:
                    permiso = PermisoInstitucional.objects.get(pk=request.POST['ids'])
                    if permiso.tipopermisodetalle.id==detalle.id:
                        pedirarchivo = False
                return JsonResponse({"result": "ok", "pedirarchivo":pedirarchivo, "fdesde":calculo_fecha_dias_plazo(detalle.diasplazo, detalle.aplicar), "count":permisosfamilia.count(), "permisofamilia":[{"id":permisofamilia.id,"integrante":permisofamilia.__str__()} for permisofamilia in permisosfamilia]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'validarfechadiasplazo':
            try:
                ne = request.POST['ne']
                detalle = TipoPermisoDetalle.objects.get(pk=int(request.POST['id']))
                mensaje=''
                cumple = True
                marzoo = 0
                detallekardex=None
                horadesde = request.POST['horadesde']
                horahasta = request.POST['horahasta']
                distributivo =DistributivoPersona.objects.get(id= int(request.POST['id_denominacionpuesto']))
                fd = convertir_fecha(request.POST['fd'])
                ff = convertir_fecha(request.POST['ff'])
                if not ne[:1] == 'e':
                    puedeadicionar = False
                    if detalle.tipopermiso_id == 12 or detalle.tipopermiso_id == 27 or detalle.tipopermiso_id == 24:
                        cumple= verificar_si_tiene_saldo_vacaciones_1(detalle.tipopermiso_id,horadesde, horahasta,persona,fd,ff,distributivo.id)
                        if detalle.tipopermiso_id == 27 or detalle.tipopermiso_id == 24:
                            if KardexVacacionesDetalle.objects.values('id').filter(status=True, kardex__persona=persona,
                                                                                   kardex__regimenlaboral=distributivo.regimenlaboral,
                                                                                   kardex__estado=1).exists():
                                detallekardex = KardexVacacionesDetalle.objects.filter(status=True,
                                                                                           kardex__persona=persona,
                                                                                           kardex__regimenlaboral=distributivo.regimenlaboral,
                                                                                           kardex__estado=1).latest('id')
                            # if detallekardex:
                            #     if distributivo.regimenlaboral_id!=2:
                            #         dias = detallekardex.diasal
                            #         if dias<=30 and cumple:
                            #             if fd.month == 3 and ff.month == 3:
                            #                 cumple = True
                            #             else:
                            #                 cumple = False
                            #                 marzoo=1
                            #                 mensaje += "DEBE SELECCIONAR SOLO EN EL MES DE MARZO"
                            #     elif distributivo.regimenlaboral_id==2 or str(persona.id) in variable_valor('PERSONAS_HABILITAN_VACACIONES'):
                            #         fimarzo=convertir_fecha_invertida(str('2020-03-01'))
                            #         # ffmarzo=convertir_fecha_invertida(str('2020-03-31'))
                            #         # fiabril=convertir_fecha_invertida(str('2020-04-01'))
                            #         ffabril=convertir_fecha_invertida(str('2020-04-09'))
                            #         fiseptiembre=convertir_fecha_invertida(str('2020-09-14'))
                            #         ffseptiembre=convertir_fecha_invertida(str('2020-09-27'))
                            #         fidiciembre=convertir_fecha_invertida(str('2020-12-15'))
                            #         ffdiciembre=convertir_fecha_invertida(str('2020-12-31'))
                            #         if (fd>=fimarzo and fd <=ffabril) and (ff>=fimarzo and ff<=ffabril) and cumple:
                            #             cumple = True
                            #         elif (fd>=fiseptiembre and fd <=ffseptiembre) and (ff>=fiseptiembre and ff<=ffseptiembre)  and cumple:
                            #             cumple=True
                            #         elif (fd >= fidiciembre and fd <= ffdiciembre) and (ff >= fidiciembre and ff <= ffdiciembre)  and cumple:
                            #             cumple=True
                            #         else:
                            #             cumple=False
                            #             marzoo = 1
                            #             mensaje += "DEBE SELECCIONAR SOLO EN LAS FECHAS DE: 01 MARZO AL 09 DE ABRIL, DEL 14 AL 27 DE SEPTIEMBRE Y DEL 15 AL 31 DE DICIEMBRE O NO TIENE SUFICIENTE SALDO DE VACACIONES"
                    resultado = valida_este_en_fecha(detalle,convertir_fecha(request.POST['fd']))
                    fecha = resultado[2]
                    if not resultado[0]:
                        mensaje = resultado[1]
                    resultado_valida_dia = valida_este_en_dias(detalle, fd, ff)
                    if resultado_valida_dia[0] and resultado[0]:
                        puedeadicionar = True
                    if not resultado_valida_dia[0]:
                        if not mensaje == '':
                            mensaje +=" Y "+resultado_valida_dia[1]
                        else:
                            mensaje = resultado_valida_dia[1]
                    if cumple==True and puedeadicionar==True:
                        puedeadicionar=True
                    elif (cumple==False and puedeadicionar==True ) or (cumple==False and puedeadicionar==False):
                        puedeadicionar = False
                        if marzoo==0:
                            mensaje+=" NO TIENE SALDO DE VACACIONES"
                    return JsonResponse({"result": "ok",'fecha':fecha, 'puedeadicionar':puedeadicionar, "mensaje":mensaje,"descuentovacaciones":detalle.descuentovacaciones})
                else:
                    if detalle.tipopermiso_id == 12 or detalle.tipopermiso_id == 27 or detalle.tipopermiso_id == 24:
                        cumple = verificar_si_tiene_saldo_vacaciones_1(detalle.tipopermiso_id, horadesde,horahasta,persona,fd,ff,distributivo.id)
                        if detalle.tipopermiso_id == 27 or detalle.tipopermiso_id == 24:
                            if KardexVacacionesDetalle.objects.values('id').filter(status=True, kardex__persona=persona,
                                                                                   kardex__regimenlaboral=distributivo.regimenlaboral,
                                                                                   kardex__estado=1).exists():
                                detallekardex = KardexVacacionesDetalle.objects.filter(status=True,
                                                                                           kardex__persona=persona,
                                                                                           kardex__regimenlaboral=distributivo.regimenlaboral,
                                                                                           kardex__estado=1).latest('id')
                            # if detallekardex:
                            #     dias = detallekardex.diasal
                            #     if dias<=30 and cumple:
                            #         if fd.month == 3 and ff.month == 3:
                            #             cumple = True
                            #         else:
                            #             cumple = False
                            #             marzoo=1
                            #             mensaje += "DEBE SELECCIONAR SOLO EN EL MES DE MARZO"
                    if not cumple and marzoo==0:
                        mensaje = 'NO TIENE SALDO DE VACACIONES'
                    return JsonResponse({"result": "ok", 'puedeadicionar': cumple,"mensaje":mensaje,"descuentovacaciones":detalle.descuentovacaciones})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al elminar los datos."})

        elif action == 'listapermisos':
            try:
                regimenlaboralpersona = extraer_regimen_laboral_antes_guardar(int(request.POST['id']))
                if regimenlaboralpersona:
                    tipospermiso = TipoPermiso.objects.filter(tipopermisoregimenlaboral__regimenlaboral=regimenlaboralpersona, status=True, tipopermisodetalle__tipopermiso__isnull=False, tipopermisodetalle__vigente=True).distinct()
                    return JsonResponse({"result": "ok", "tipospermiso":[{"id":tipopermiso.id, "descripcion":tipopermiso.descripcion} for tipopermiso in tipospermiso]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'permisodetalle':
            try:
                tipopermiso = TipoPermiso.objects.get(pk=request.POST['id'])
                lista = []
                listacategoria = []
                si = 2
                aux=0
                regimen=None
                fi1=ff1=fi2=ff2=None
                horainicio='08:00'
                horafin='17:00'
                detallekardex=None
                if 'ENFERMEDAD' in tipopermiso.descripcion:
                    si = 1
                for dettalle in tipopermiso.tipopermisodetalle_set.filter(status=True, vigente=True):
                    lista.append([dettalle.id,dettalle.__str__(), 1 if dettalle.perdirarchivo else 0])
                for detalle in tipopermiso.categoriatipopermiso_set.filter(status=True, tipopermiso__isnull=False):
                    listacategoria.append([detalle.id,detalle.descripcion.upper(),1])
                # if tipopermiso.id == 27 or tipopermiso.id == 24:
                #     if DistributivoPersona.objects.filter(id=int(request.POST['id_denominacionpuesto'])).exists():
                #         regimen = DistributivoPersona.objects.filter(id=int(request.POST['id_denominacionpuesto']))[0].regimenlaboral
                #         if KardexVacacionesDetalle.objects.values('id').filter(status=True, kardex__persona=persona, kardex__regimenlaboral=regimen, kardex__estado=1).exists():
                #             detallekardex = KardexVacacionesDetalle.objects.filter(status=True, kardex__persona=persona, kardex__regimenlaboral=regimen, kardex__estado=1).latest('id')
                #             if regimen.id!=2 and not str(persona.id) in variable_valor('PERSONAS_HABILITAN_VACACIONES'):
                #                 dias = detallekardex.diasal
                #                 if dias>=31 and dias <=40:
                #                     aux=1
                #                     fi1 = '02-03-2020'
                #                     ff1 = convertir_fecha_invertida(str(convertir_fecha(fi1)+timedelta(days=(dias-1))))
                #                     ff1='%s-%s-%s'%(ff1.day,ff1.month,ff1.year)
                #                 elif dias >40:
                #                     aux=2
                #                     fi1 = '02-03-2020'
                #                     ff1 ='09-04-2020'
                #                     fi2 = '14-09-2020'
                #                     diasrestante= dias-40
                #                     if diasrestante <=14:
                #                         ff2 = convertir_fecha_invertida(str(convertir_fecha(fi2) + timedelta(days=(diasrestante-1))))
                #                         ff2 = '%s-%s-%s' % (ff2.day, ff2.month, ff2.year)
                #                     else:
                #                         ff2 ='27-09-2020'
                #                         diasrestante1=dias-54
                #                         ff1 = convertir_fecha_invertida(str(convertir_fecha(ff1) + timedelta(days=(diasrestante1-1))))
                #                         ff1 = '%s-%s-%s' % (ff1.day, ff1.month, ff1.year)
                #                 else:
                #                     aux=5
                #                     # ff2 = convertir_fecha('%s/09/2020'%diasrestante)
                #                     # ff2='%s-%s-%s'%(ff2.day,ff2.month,ff2.year)
                #         else:
                #             JsonResponse({"result": "bad", "mensaje": u"No tiene saldo vacaciones."})
                return JsonResponse({'result': 'ok', 'lista': lista, 'count': len(lista),'si':si,'aux':aux,'fi1':fi1,'ff1':ff1,'fi2':fi2,'ff2':ff2,'listacat':listacategoria,'countl':len(listacategoria)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addarchivo':
            try:
                f = PermisoInstitucionalForm(request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            if not ext == '.PDF':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("Solicitud", newfile._name)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    permiso = PermisoInstitucional.objects.get(pk=int(request.POST['id']))
                    permiso.archivo = newfile
                    if permiso.estadosolicitud==6:
                        permiso.estadosolicitud = 1
                        destinatario = permiso.permisoaprobacion_set.filter(estadosolicitud=4,
                                                                            status=True).last().aprueba
                        notificacion('Permiso institucional de %s' % permiso, ('Se ha modificado el permiso: %s ' % permiso),
                                     destinatario,
                                     None, ('/th_aprobarpermiso_th?s=%s' % permiso.solicita.identificacion()),
                                     permiso.pk,
                                     1, 'sga-sagest', PermisoInstitucional, request)
                    permiso.save(request)

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'adicionar':
                try:
                    data['title'] = u'Solicitar Permiso Institucional'
                    form = PermisoInstitucionalForm(initial={'fechasolicitud': datetime.now().date()})
                    form.adicionar(persona)
                    form.deshabilitar_permisofamilia()
                    data['form2'] = PermisoInstitucionalDetalleForm()
                    data['fecha'] = str(datetime.now().date())[8:10] + '-' + str(datetime.now().date())[5:7] + '-' + str(datetime.now().date())[:4]
                    data['hora'] = str(datetime.now())[11:16]
                    data['form'] = form
                    return render(request, "th_permiso_institucional/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Solicitar Permiso Institucional'
                    data['permiso'] = permiso = PermisoInstitucional.objects.get(pk=int(request.GET['id']))
                    distributivo = DistributivoPersona.objects.filter(persona=permiso.solicita,denominacionpuesto=permiso.denominacionpuesto, status=True,estadopuesto__id=PUESTO_ACTIVO_ID).distinct()
                    form = PermisoInstitucionalForm(initial={'fechasolicitud': permiso.fechasolicitud,
                                                             'puesto': permiso.denominacionpuesto,
                                                             'tiposolicitud': permiso.tiposolicitud,
                                                             'tipopermiso': permiso.tipopermiso,
                                                             'tipopermisodetalle': permiso.tipopermisodetalle,
                                                             'denominacionpuesto': distributivo[0],
                                                             'permisofamilia': permiso.permisofamilia,
                                                             'motivo': permiso.motivo,
                                                             'casasalud':permiso.casasalud,
                                                             'categoriapermiso':permiso.categoriatipopermiso})
                    form.editar(permiso)
                    if not permiso.permisofamilia:
                        form.deshabilitar_permisofamilia()
                    data['form2'] = PermisoInstitucionalDetalleForm()
                    data['fecha'] = str(datetime.today())[8:10] + '-' + str(datetime.today())[5:7] + '-' + str(datetime.today())[:4]
                    data['hora'] = str(datetime.today())[11:16]
                    data['form'] = form
                    data['detalles'] = permiso.permisoinstitucionaldetalle_set.all()
                    return render(request, "th_permiso_institucional/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'del_permiso':
                try:
                    data['title'] = u'Eliminar permiso institucional'
                    data['permiso'] = PermisoInstitucional.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_permiso_institucional/delete.html", data)
                except:
                    pass

            elif action == 'detalle':
                try:
                    data = {}
                    detalle = PermisoInstitucional.objects.get(pk=int(request.GET['id']))
                    data['permiso'] = detalle
                    data['detallepermiso'] = detalle.permisoinstitucionaldetalle_set.filter(status=True)
                    data['aprobadores'] = detalle.permisoaprobacion_set.all()
                    template = get_template("th_permiso_institucional/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mikardex':
                try:
                    search=None
                    ids=None
                    if IngresoPersonal.objects.filter(persona=persona).exists():
                        data['ingresopersonal']=kardex=IngresoPersonal.objects.filter(persona=persona)
                        data['primerregistro']=IngresoPersonal.objects.filter(persona=persona)[0]
                        data['title'] = 'Detalle Kardex de Vacaciones'
                        # if kardex.kardexvacacionesdetalle_set.exists():
                        #     detalle=kardex.kardexvacacionesdetalle_set.filter(status=True).order_by("-fecha","-id")

                            # paging = MiPaginador(detalle, 25)
                            # p = 1
                            # try:
                            #     paginasesion = 1
                            #     if 'paginador' in request.session:
                            #         paginasesion = int(request.session['paginador'])
                            #     if 'page' in request.GET:
                            #         p = int(request.GET['page'])
                            #     else:
                            #         p = paginasesion
                            #     try:
                            #         page = paging.page(p)
                            #     except:
                            #         p = 1
                            #     page = paging.page(p)
                            # except:
                            #     page = paging.page(p)
                            # request.session['paginador'] = p
                            # data['paging'] = paging
                            # data['page'] = page
                            # data['rangospaging'] = paging.rangos_paginado(p)
                            # data['detalle'] = page.object_list
                            # data['search'] = search if search else ""
                            # data['ids'] = ids if ids else ""
                        return render(request, 'th_permiso_institucional/detallekardexpersonal.html', data)
                    else:
                        return HttpResponseRedirect('/th_permiso?info=No registra días de vacaciones.')
                    # else:
                    #     return HttpResponseRedirect('/th_permiso?info=No registra días de vacaciones.')
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            if not DistributivoPersona.objects.filter(persona=persona):
                return HttpResponseRedirect('/?info=Ud. no tiene asignado un cargo, favor comunicarse con talento humano.')
            data['title'] = u'Solicitud de Permiso Institucional.'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                plantillas = PermisoInstitucional.objects.select_related().filter(status=True, solicita=persona).filter(Q(motivo__contains=search) |
                                                                                                       Q(solicita__cedula__icontains=search) |
                                                                                                       Q(solicita__pasaporte__icontains=search)).distinct().order_by('-fechasolicitud', '-secuencia')
            elif 'id' in request.GET:
                ids = request.GET['id']
                plantillas = PermisoInstitucional.objects.select_related().filter(id=ids, solicita=persona)
            else:
                plantillas = PermisoInstitucional.objects.select_related().filter(status=True, solicita=persona).order_by('-fechasolicitud', '-secuencia')
            paging = MiPaginador(plantillas, 20)
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
            data['permisos'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['form2'] = PemisoInstitucionalArchivoForm()
            return render(request, 'th_permiso_institucional/view.html', data)


def calculo_fecha_dias_plazo(diasplazo, dias_antes_despues, fechaempezar=None):
    if fechaempezar:
        fecha = fechaempezar
    else:
        fecha = datetime.now().date()
    aumento = 1
    while aumento <= diasplazo:
        dias = None
        if dias_antes_despues == 1:
                dias = timedelta(days=1)
        elif dias_antes_despues == 2:
                dias = timedelta(days=-1)
        fecha = fecha + dias
        aumento += 1
    return fecha.strftime('%d-%m-%Y')

def extraer_regimen_laboral_antes_guardar(distributivo_id):
        distributivo = DistributivoPersona.objects.filter(pk=distributivo_id)
        if distributivo.exists():
            return distributivo[0].regimenlaboral
        else:
            return None

def valida_este_en_fecha(tipopermisodetalle, fechadesde, fechasolicitud=None):
    mensaje = ''
    puedeadicionar = False
    fecha = datetime.strptime(calculo_fecha_dias_plazo(tipopermisodetalle.diasplazo, tipopermisodetalle.aplicar, fechasolicitud if fechasolicitud else None), '%d-%m-%Y').date()
    if tipopermisodetalle.aplicar == 1:
        if fechadesde >= fecha:
            puedeadicionar = True
        else:
            puedeadicionar = False
            mensaje = "DEBERÁ SOLICITAR  " + ('HASTA ' if tipopermisodetalle.aplicar == 2 else '') + tipopermisodetalle.diasplazo.__str__() +' DÍAS '+ tipopermisodetalle.get_aplicar_display().__str__()
    elif tipopermisodetalle.aplicar == 2:
        if fechadesde >= fecha:
            puedeadicionar = True
        else:
            puedeadicionar = False
            mensaje = "DEBERÁ SOLICITAR  " + ('HASTA ' if tipopermisodetalle.aplicar == 2 else '') + tipopermisodetalle.diasplazo.__str__() + ' DÍAS ' + tipopermisodetalle.get_aplicar_display().__str__()
    return [puedeadicionar, mensaje, fecha]


def valida_este_en_dias(tipopermisodetalle, fechainicio, fechafin):
    fechaini = fechainicio
    contador = 0
    mensaje = ''
    puedeadicionar = False
    while fechaini <= fechafin:
        fechaini = fechaini + timedelta(days=1)
        contador += 1
    if contador <= tipopermisodetalle.dias:
        puedeadicionar = True
    else:
        mensaje = "EL PERMISO NO PUEDE EXCEDER MÁS DE "+tipopermisodetalle.dias.__str__()+" DÍAS"
    return [puedeadicionar, mensaje]

def verificar_si_tiene_saldo_vacaciones_1(tipopermiso,horadesde,horahasta,persona,fd,ff, iddistributivo):
    cumple = False
    if tipopermiso == 12 or tipopermiso == 27 or tipopermiso == 24:
        dsitributivo = DistributivoPersona.objects.get(id=iddistributivo)
        if KardexVacacionesDetalle.objects.values_list('id').filter(status=True, kardex__persona=persona, kardex__regimenlaboral=dsitributivo.regimenlaboral).exists():
            inicio = horadesde.split(':')
            fin = horahasta.split(':')
            detallekardex = KardexVacacionesDetalle.objects.filter(status=True, kardex__persona=persona, kardex__regimenlaboral=dsitributivo.regimenlaboral).latest('id')
            tomavacaciones = ff - fd
            saldo = timedelta(days=detallekardex.diasal, hours=detallekardex.horasal, minutes=detallekardex.minsal)
            inicio = timedelta(hours=int(inicio[0]), minutes=int(inicio[1]))
            fin = timedelta(hours=int(fin[0]), minutes=int(fin[1]))
            total = fin - inicio
            horas = total.seconds // 3600
            minutos = (total.seconds // 60) - (horas * 60)
            permisos = timedelta(days=tomavacaciones.days, hours=horas, minutes=minutos)
            if detallekardex.diasal < 1 and detallekardex.horasal < 1 and detallekardex.minsal < 1:
                cumple = False
            elif saldo < permisos:
                cumple = False
            else:
                cumple=True
    return cumple

def verificar_si_tiene_saldo_vacaciones(tipopermiso,horadesde,horahasta,persona, denominacionpuesto):
    cumple = True
    detallekardex=None
    if tipopermiso == 12 or tipopermiso == 27 or tipopermiso == 24:
        if KardexVacacionesDetalle.objects.filter(status=True, kardex__persona=persona).exists():
            inicio = horadesde.split(':')
            fin = horahasta.split(':')
            if DistributivoPersona.objects.filter(persona=persona, denominacionpuesto__id=denominacionpuesto).exists():
                regimen = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto__id=denominacionpuesto)[0].regimenlaboral
                if KardexVacacionesDetalle.objects.filter(status=True, kardex__persona=persona, kardex__regimenlaboral=regimen).exists():
                    detallekardex = KardexVacacionesDetalle.objects.filter(status=True, kardex__persona=persona, kardex__regimenlaboral=regimen).latest('id')
            else:
                detallekardex = KardexVacacionesDetalle.objects.filter(status=True, kardex__persona=persona).latest('id')
            if detallekardex:
                saldo = timedelta(days=detallekardex.diasal, hours=detallekardex.horasal, minutes=detallekardex.minsal)
                inicio = timedelta(hours=int(inicio[0]), minutes=int(inicio[1]))
                fin = timedelta(hours=int(fin[0]), minutes=int(fin[1]))
                total = fin - inicio
                horas = total.seconds // 3600
                minutos = (total.seconds // 60) - (horas * 60)
                permisos = timedelta(days=0, hours=horas, minutes=minutos)
                if detallekardex.diasal < 1 and detallekardex.horasal < 1 and detallekardex.minsal < 1:
                    cumple = False
                elif saldo < permisos:
                    cumple = False
            else:
                cumple = False
    return cumple


def numero_saldo_vacaciones(persona, denominacionpuesto):
    regimen=None
    if DistributivoPersona.objects.filter(persona=persona, denominacionpuesto=denominacionpuesto).exists():
        regimen = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto=denominacionpuesto)[0].regimenlaboral

    if regimen:
        kardex =IngresoPersonal.objects.filter(status=True, persona=persona, estado=1, regimenlaboral=regimen).order_by("-id")[0]
    else:
        kardex = IngresoPersonal.objects.filter(status=True, persona=persona, estado=1).order_by("-id")[ 0]
    detallekardex = kardex.kardexvacacionesdetalle_set.filter(kardex__persona=persona).latest('id')
    if detallekardex:
        saldo = detallekardex.diasal
    else:
        saldo = 0
    return saldo

