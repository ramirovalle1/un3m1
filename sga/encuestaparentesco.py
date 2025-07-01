# -*- coding: latin-1 -*-
import json
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime

from decorators import  last_access
from sagest.models import  Congreso,  TipoParticipacionCongreso
from sga.models import Persona, Matricula,  Graduado, RANGO_EDAD_NINO,\
    MESES_EMBARAZO, Periodo, PersonaDatosFamiliares



@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addregistro':
                try:
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip()
                    nummiembros = int(request.POST['id_nummiembros'])
                    rangoedad = json.loads(request.POST['lista_items'])
                    id_tienediscapacidad = int(request.POST['id_tienediscapacidad'])
                    id_estadogestacion = int(request.POST['id_estadogestacion'])
                    id_niniera = int(request.POST['id_niniera'])
                    aceptaservicio = int(request.POST['id_aceptaservicio'])
                    id_tienehijos = int(request.POST['id_tienehijos'])
                    mesembarazo = request.POST['id_mesembarazo']

                    if id_tienehijos==1:
                        tienehijos=True
                    else:
                        tienehijos=False


                    if id_tienediscapacidad==1:
                        tienediscapacidad=True
                    else:
                        tienediscapacidad=False

                    if id_estadogestacion==1:
                        estadogestacion=True
                    else:
                        estadogestacion=False


                    if id_niniera==1:
                        niniera=True
                    else:
                        niniera=False

                    if Persona.objects.filter(Q(cedula__icontains=cedula) |Q(pasaporte__icontains=cedula)).exists():
                        if Persona.objects.filter(cedula=cedula).exists():
                            datospersona = Persona.objects.filter(cedula=cedula)[0]
                        elif Persona.objects.filter(pasaporte=cedula).exists():
                            datospersona = Persona.objects.filter(pasaporte=cedula)[0]
                        datospersona.estadogestacion = estadogestacion
                        datospersona.mesembarazo = mesembarazo
                        datospersona.niniera = niniera
                        datospersona.aceptaservicio = aceptaservicio
                        datospersona.numeromiembrosfamilia = nummiembros
                        datospersona.save(request)
                        if tienehijos:
                            for x in rangoedad:
                                if not PersonaDatosFamiliares.objects.values('id').filter(persona=datospersona, parentesco__id__in= [11,14], status=True,rangoedad=int(x['idrango']) ).exists():
                                    familiar = PersonaDatosFamiliares(persona=datospersona, parentesco_id=11,
                                                                       tienediscapacidad=tienediscapacidad,
                                                                        rangoedad=int(x['idrango']),
                                                                        nacimiento=datetime.now().date(),
                                                                       )
                                    familiar.save(request)
                                else:
                                    familiar=PersonaDatosFamiliares.objects.filter(persona=datospersona, parentesco__id__in=[11,14], status=True ,rangoedad=int(x['idrango']))[0]
                                    familiar.tienediscapacidad=tienediscapacidad
                                    familiar.rangoedad=int(x['idrango'])
                                    familiar.save(request)

                        # return HttpResponseRedirect('/')
                        return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'consultacedula':
                try:
                    if 'cedula' in request.POST:
                        cedula = request.POST['cedula'].strip()
                        if cedula!='':
                            datospersona = None
                            edad = 0
                            inscripcion = None
                            matricula = None
                            if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)| Q(ruc=cedula)).exists():
                                if Persona.objects.filter(cedula=cedula).exists():
                                    datospersona = Persona.objects.filter(cedula=cedula)[0]
                                elif Persona.objects.filter(pasaporte=cedula).exists():
                                    datospersona = Persona.objects.filter(pasaporte=cedula)[0]
                                if datospersona.aceptaservicio == 0 or datospersona.aceptaservicio == None:
                                    periodo=Periodo.objects.get(id=90)
                                    if datospersona.inscripcion_set.values('id').filter(status=True, activo=True).exists():
                                        inscripcion=datospersona.inscripcion_set.filter(status=True, activo=True)[0]
                                        if inscripcion.matricula_periodo(periodo):
                                            matricula=inscripcion.matricula_periodo(periodo)
                                    edad=int(datetime.now().date().year - datospersona.nacimiento.year) if datospersona.nacimiento else 0
                                    return JsonResponse({"result": "ok",
                                                         "nombres": datospersona.nombre_completo_inverso(),
                                                         "estadocivil": str(datospersona.estado_civil()),
                                                         "telefono": datospersona.telefono,
                                                         "direccion": datospersona.direccion_completa(),
                                                         "genero":datospersona.sexo.nombre if datospersona.sexo else"",
                                                         "canton": str(datospersona.canton),"edad":edad,
                                                         "carrera": str(inscripcion.carrera) if inscripcion else "",
                                                         "facultad": str(inscripcion.carrera.coordinaciones()[0]) if inscripcion else "",
                                                         "nivel": str(matricula.nivelmalla) if matricula else "",
                                                         "seccion": str(inscripcion.sesion) if inscripcion else "",
                                                         "idgenero":datospersona.sexo.id if datospersona.sexo else 0,
                                                         })
                                else:
                                    return JsonResponse({"result": "ok2", })
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"No puede realizar la encuesta."})
                        else:
                            return JsonResponse({"result": "ok3", })
                    else:
                        return JsonResponse({"result": "ok3", })
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'verificaparticipacion':
                try:
                    codigocurso = Congreso.objects.get(pk=request.POST['id'])
                    participaciones = TipoParticipacionCongreso.objects.filter(status=True, congreso=codigocurso)
                    lista = []
                    for part in participaciones:
                        lista.append([part.id, part.nombre_completo()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'validarparticipacion':
                try:
                    participacion = request.POST['participacion'].strip()
                    participacion = TipoParticipacionCongreso.objects.get(status=True, id=participacion)
                    if participacion.tipoparticipante_id in [2,4,5,10,11]:
                        cedula = request.POST['cedula'].strip()
                        datospersona = None
                        if Persona.objects.filter(cedula=cedula, status=True).exists():
                            datospersona = Persona.objects.get(cedula=cedula, status=True)
                        if Persona.objects.filter(pasaporte=cedula, status=True).exists():
                            datospersona = Persona.objects.get(pasaporte=cedula, status=True)
                        if not datospersona:
                                return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como usuario de UNEMI" })
                        else:
                            # DOCENTES
                            if participacion.tipoparticipante_id in [4,10]:
                                if not datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True, regimenlaboral__id=2).exists():
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, con consta como docente de UNEMI"})
                            elif participacion.tipoparticipante_id in [2,11]:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    if not Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True, cerrada=False).exists():
                                            return JsonResponse({"result": "bad", "costocurso": "Ud, no consta con una matrícula activa en UNEMI"})
                                else:
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta con una matrícula activa en UNEMI"})
                            elif participacion.tipoparticipante_id == 5:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    if not Graduado.objects.filter(inscripcion__id__in=verificainsripcion, status=True).exists():
                                        return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI"})
                                else:
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI"})
                    return JsonResponse({"result": "ok", "costocurso": participacion.valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'encuesta':
                try:
                    data['title'] = u'DIRECCIÓN DE BIENESTAR UNIVERSITARIO Y ESTUDIANTIL ENCUESTA'
                    data['randoedad'] = RANGO_EDAD_NINO
                    data['cedula'] =''
                    if 'cedula' in request.GET:
                        data['cedula'] = request.GET['cedula']
                    data['mesesembarazo'] = MESES_EMBARAZO
                    return render(request, "encuestaparentesco/encuestaparentesco.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'
                hoy = datetime.now().date()
                cursos = None
                return render(request, "encuestaparentesco/encuestaparentesco.html", data)
            except Exception as ex:
                pass