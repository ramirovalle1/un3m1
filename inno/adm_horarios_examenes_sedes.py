# -*- coding: latin-1 -*-
import json
import random

from django.core.exceptions import ObjectDoesNotExist
from xlwt import Workbook
from xlwt import *
from django.forms.models import model_to_dict
from django.template import Context
from django.template.loader import get_template
import sys
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import Q, F, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from inno.forms import SedeVirtualForm, LaboratorioVirtualForm, FechaPlanificacionSedeVirtualExamenForm, \
    HorarioPlanificacionSedeVirtualExamenForm, AulaPlanificacionSedeVirtualExamenForm, SedeVirtualPeriodoForm, \
    SedeProvinciasForm
from inno.funciones import generar_clave_aleatoria
from inno.models import MatriculaSedeExamen, FechaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen, SedeProvincia
from inno.runBackGround import ReportPlanificacionSedes, ReportHorariosExamenesSedes, ReportPlanificacionExamenes
from sga.commonviews import adduserdata, traerNotificaciones
from sga.excelbackground import reporte_persona_sin_examen
from sga.funciones import log, puede_realizar_accion, MiPaginador, generar_nombre
from sga.models import Nivel, Materia, MateriaAsignada, SedeVirtual, LaboratorioVirtual, Notificacion, Malla, Matricula, \
    DetalleModeloEvaluativo, TipoAula, Persona, SedeVirtualPeriodoAcademico
from sga.templatetags.sga_extras import encrypt
from inno.serializers.HorarioExamen import SedeVirtualSerializer, FechaPlanificacionSedeVirtualExamenSerializer, \
    TurnoPlanificacionSedeVirtualExamenSerializer, AulaPlanificacionSedeVirtualExamenSerializer, \
    MateriaAsignadaPlanificacionSedeVirtualExamenSerializer, PersonaSerializer


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'saveCampusVirtual':
            try:
                id = 0
                if 'id' in request.POST:
                    id = int(encrypt(request.POST['id']))
                fotofile = None
                if 'foto' in request.FILES:
                    fotofile = request.FILES['foto']
                    if fotofile.size > 8194304:
                        raise NameError(u"Archivo mayor a 8Mb.")
                    fotofileod = fotofile._name
                    ext = fotofileod[fotofileod.rfind("."):]
                    if not ext in ['.jpg', '.png', '.jpeg']:
                        raise NameError(u"Solo archivo con extensión. jpg png o jpeg")
                    fotofile._name = generar_nombre("foto_sedevirtual_", fotofile._name)
                form = SedeVirtualForm(request.POST, request.FILES)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])

                if id != 0:
                    puede_realizar_accion(request, 'inno.puede_editar_sedevirtual')
                    eSedeVirtual = SedeVirtual.objects.get(pk=id)
                    eSedeVirtual.nombre = form.cleaned_data['nombre']
                    eSedeVirtual.activa = form.cleaned_data['activa']
                    eSedeVirtual.principal = form.cleaned_data['principal']
                    eSedeVirtual.referencias = form.cleaned_data['referencias']
                    eSedeVirtual.latitud = form.cleaned_data['latitud'] if form.cleaned_data['latitud'] else None
                    eSedeVirtual.longitud = form.cleaned_data['longitud'] if form.cleaned_data['longitud'] else None
                    if not eSedeVirtual.foto:
                        eSedeVirtual.foto = fotofile
                    eSedeVirtual.save(request)
                    log(u'Edito sede virtual: %s' % eSedeVirtual, request, 'edit')
                else:
                    puede_realizar_accion(request, 'inno.puede_crear_sedevirtual')
                    eSedeVirtual = SedeVirtual(nombre=form.cleaned_data['nombre'],
                                               activa=form.cleaned_data['activa'],
                                               principal=form.cleaned_data['principal'],
                                               referencias=form.cleaned_data['referencias'],
                                               foto=fotofile,
                                               latitud=form.cleaned_data['latitud'] if form.cleaned_data['latitud'] else None,
                                               longitud=form.cleaned_data['longitud'] if form.cleaned_data['longitud'] else None)
                    eSedeVirtual.save(request)
                    log(u'Adiciono sede virtual: %s' % eSedeVirtual, request, 'add')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'saveCampusVirtualPeriodo':
            try:
                id = request.POST.get('id', 0)
                if id == 0:
                    raise NameError(u"Sede virtual no encontrada")
                form = SedeVirtualPeriodoForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                puede_realizar_accion(request, 'inno.puede_editar_sedevirtual')
                try:
                    eSedeVirtualPeriodoAcademico = SedeVirtualPeriodoAcademico.objects.get(sedevirtual_id=id, periodo=form.cleaned_data['periodo'])
                except ObjectDoesNotExist:
                    eSedeVirtualPeriodoAcademico = SedeVirtualPeriodoAcademico(sedevirtual_id=id,
                                                                               periodo=form.cleaned_data['periodo'])
                eSedeVirtualPeriodoAcademico.save(request)
                log(u'Adiciono period a la sede virtual: %s' % eSedeVirtualPeriodoAcademico, request, 'add')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteSedeVirtualPeriodoAcademico':
            try:
                try:
                    eSedeVirtualPeriodoAcademico = deleSedeVirtualPeriodoAcademico = SedeVirtualPeriodoAcademico.objects.get(pk=request.POST.get('id', 0))
                except ObjectDoesNotExist:
                    raise NameError(u"No se encontro el registro a eliminar")
                eSedeVirtualPeriodoAcademico.delete()
                log(u"Quito periodo de sede: %s" % deleSedeVirtualPeriodoAcademico, request, "del")
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteCampusVirtual':
            try:
                puede_realizar_accion(request, 'inno.puede_eliminar_sedevirtual')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not SedeVirtual.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro a eliminar")
                eSedeVirtual = deleteSede = SedeVirtual.objects.get(pk=request.POST['id'])
                eSedeVirtual.delete()
                log(u'Elimino sede virtual: %s' % deleteSede, request, 'del')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'saveAulaVirtual':
            try:
                id = 0
                if 'id' in request.POST:
                    id = int(encrypt(request.POST['id']))
                form = LaboratorioVirtualForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if id != 0:
                    puede_realizar_accion(request, 'inno.puede_editar_aulavirtual')
                    eLaboratorioVirtual = LaboratorioVirtual.objects.get(pk=id)
                    eLaboratorioVirtual.sedevirtual=form.cleaned_data['sedevirtual']
                    eLaboratorioVirtual.tipo=form.cleaned_data['tipo']
                    eLaboratorioVirtual.bloque=form.cleaned_data['bloque'] if form.cleaned_data['bloque'] else None
                    eLaboratorioVirtual.nombre=form.cleaned_data['nombre']
                    eLaboratorioVirtual.capacidad=form.cleaned_data['capacidad']
                    eLaboratorioVirtual.activo=form.cleaned_data['activo']
                    eLaboratorioVirtual.save(request)
                    log(u'Edito aula virtual: %s' % eLaboratorioVirtual, request, 'edit')
                else:
                    puede_realizar_accion(request, 'inno.puede_crear_aulavirtual')
                    eLaboratorioVirtual = LaboratorioVirtual(sedevirtual=form.cleaned_data['sedevirtual'],
                                                             tipo=form.cleaned_data['tipo'],
                                                             bloque=form.cleaned_data['bloque'] if form.cleaned_data['bloque'] else None,
                                                             nombre=form.cleaned_data['nombre'],
                                                             capacidad=form.cleaned_data['capacidad'],
                                                             activo=form.cleaned_data['activo']
                                                             )
                    eLaboratorioVirtual.save(request)
                    log(u'Adiciono aula virtual: %s' % eLaboratorioVirtual, request, 'add')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteAulaVirtual':
            try:
                puede_realizar_accion(request, 'inno.puede_eliminar_aulavirtual')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not LaboratorioVirtual.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro a eliminar")
                eLaboratorioVirtual = deleteAula = LaboratorioVirtual.objects.get(pk=request.POST['id'])
                eLaboratorioVirtual.delete()
                log(u'Elimino aula virtual: %s' % deleteAula, request, 'del')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'saveFechaPlanificacion':
            try:
                if not 'ids' in request.POST:
                    raise NameError(u"No se encontro la sede")
                ids = int(encrypt(request.POST['ids']))
                if not SedeVirtual.objects.values("id").filter(pk=ids).exists():
                    raise NameError(u"No se encontro la sede")
                eSedeVirtual = SedeVirtual.objects.get(pk=ids)
                id = 0
                if 'id' in request.POST:
                    id = int(encrypt(request.POST['id']))

                form = FechaPlanificacionSedeVirtualExamenForm(request.POST)
                form.edit(request.POST['supervisor'])
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                ePeriodo = periodo
                if id != 0:
                    puede_realizar_accion(request, 'inno.puede_editar_planificacionexamenvirtual')
                    eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    if FechaPlanificacionSedeVirtualExamen.objects.values("id").filter(sede=eSedeVirtual, periodo=ePeriodo, fecha=form.cleaned_data['fecha']).exclude(pk=eFechaPlanificacionSedeVirtualExamen.pk).exists():
                        raise NameError(u"Fecha ya se encuentra planificada en esta sede")
                    eFechaPlanificacionSedeVirtualExamen.fecha=form.cleaned_data['fecha']
                    eFechaPlanificacionSedeVirtualExamen.supervisor=form.cleaned_data['supervisor']
                    eFechaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Edito fecha de planificación de horario de examen virtual: %s' % eFechaPlanificacionSedeVirtualExamen, request, 'edit')
                else:
                    puede_realizar_accion(request, 'inno.puede_crear_planificacionexamenvirtual')
                    if FechaPlanificacionSedeVirtualExamen.objects.values("id").filter(sede=eSedeVirtual, periodo=ePeriodo, fecha=form.cleaned_data['fecha']).exists():
                        raise NameError(u"Fecha ya se encuentra planificada en esta sede")
                    eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen(sede=eSedeVirtual,
                                                                                               periodo=ePeriodo,
                                                                                               fecha=form.cleaned_data['fecha'],
                                                                                               supervisor=form.cleaned_data['supervisor'])
                    eFechaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Adiciono fecha de planificación de horario de examen virtual: %s' % eFechaPlanificacionSedeVirtualExamen, request, 'add')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteFechaPlanificacion':
            try:
                puede_realizar_accion(request, 'inno.puede_eliminar_planificacionexamenvirtual')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not FechaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro a eliminar")
                eFechaPlanificacionSedeVirtualExamen = deleteFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                eFechaPlanificacionSedeVirtualExamen.delete()
                log(u'Elimino fecha de planificación de horario de examen virtual: %s' % deleteFechaPlanificacionSedeVirtualExamen, request, 'del')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'saveHorarioPlanificacion':
            try:
                if not 'idf' in request.POST:
                    raise NameError(u"No se encontro la fecha de planificación")
                idf = int(encrypt(request.POST['idf']))
                if not FechaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=idf).exists():
                    raise NameError(u"No se encontro la fecha de planificación")
                eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=idf)
                id = 0
                if 'id' in request.POST:
                    id = int(encrypt(request.POST['id']))

                form = HorarioPlanificacionSedeVirtualExamenForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if id != 0:
                    puede_realizar_accion(request, 'inno.puede_editar_planificacionexamenvirtual')
                    eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    if TurnoPlanificacionSedeVirtualExamen.objects.values("id").filter(fechaplanificacion=eFechaPlanificacionSedeVirtualExamen, horainicio=form.cleaned_data['horainicio'], horafin=form.cleaned_data['horafin']).exclude(pk=eTurnoPlanificacionSedeVirtualExamen.pk).exists():
                        raise NameError(f"Horario ya se encuentra planificada en lña fecha {eFechaPlanificacionSedeVirtualExamen.fecha.__str__()}")
                    eTurnoPlanificacionSedeVirtualExamen.horainicio=form.cleaned_data['horainicio']
                    eTurnoPlanificacionSedeVirtualExamen.horafin=form.cleaned_data['horafin']
                    eTurnoPlanificacionSedeVirtualExamen.save(request)
                    log(u'Edito horario de planificación de examen virtual: %s' % eTurnoPlanificacionSedeVirtualExamen, request, 'edit')
                else:
                    puede_realizar_accion(request, 'inno.puede_crear_planificacionexamenvirtual')
                    if TurnoPlanificacionSedeVirtualExamen.objects.values("id").filter(fechaplanificacion=eFechaPlanificacionSedeVirtualExamen, horainicio=form.cleaned_data['horainicio'], horafin=form.cleaned_data['horafin']).exists():
                        raise NameError(f"Horario ya se encuentra planificada en lña fecha {eFechaPlanificacionSedeVirtualExamen.fecha.__str__()}")
                    eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen(fechaplanificacion=eFechaPlanificacionSedeVirtualExamen,
                                                                                               horainicio=form.cleaned_data['horainicio'],
                                                                                               horafin=form.cleaned_data['horafin'])
                    eTurnoPlanificacionSedeVirtualExamen.save(request)
                    log(u'Adiciono horario de planificación de examen virtual: %s' % eTurnoPlanificacionSedeVirtualExamen, request, 'add')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteHorarioPlanificacion':
            try:
                puede_realizar_accion(request, 'inno.puede_eliminar_planificacionexamenvirtual')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not TurnoPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro a eliminar")
                eTurnoPlanificacionSedeVirtualExamen = deleteTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                eTurnoPlanificacionSedeVirtualExamen.delete()
                log(u'Elimino horario de planificación de examen virtual: %s' % deleteTurnoPlanificacionSedeVirtualExamen, request, 'del')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'adicionarelacion':
            try:
                form = SedeProvinciasForm(request.POST)
                if form.is_valid():
                    provincia= form.cleaned_data['provincias']
                    sedevirtual= form.cleaned_data['sede_virtual']
                    registro = SedeProvincia(
                        sede_virtual=sedevirtual,
                        provincia=provincia
                    )
                    if SedeProvincia.objects.filter(sede_virtual=sedevirtual, provincia=provincia).exists():
                        #raise NameError(f"La relación ya existe")
                        return HttpResponseRedirect(f"{request.path}?info=La relacion ya existe")
                    registro.save()
                return HttpResponseRedirect(f"{request.path}?action=sedesprovincias")
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'editsede':
            try:
                id = request.POST['id']
                form = SedeProvinciasForm(request.POST)
                if form.is_valid():
                    provincia= form.cleaned_data['provincias']
                    sedevirtual= form.cleaned_data['sede_virtual']
                    if SedeProvincia.objects.filter(sede_virtual=sedevirtual, provincia=provincia).exists():
                        raise NameError(f"La relación sede-provincia ya existe")
                    registro_editar = SedeProvincia.objects.get(pk=id)
                    registro_editar.sede_virtual = sedevirtual
                    registro_editar.provincia = provincia
                    registro_editar.save()
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deletesede':
            try:
                id = request.POST['id']
                registro = SedeProvincia.objects.filter(pk=id)
                registro.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'saveAulaPlanificacion':
            try:
                if not 'idh' in request.POST:
                    raise NameError(u"No se encontro la horario de planificación")
                idh = int(encrypt(request.POST['idh']))
                if not TurnoPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=idh).exists():
                    raise NameError(u"No se encontro la fecha de planificación")
                eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                id = 0
                if 'id' in request.POST:
                    id = int(encrypt(request.POST['id']))

                form = AulaPlanificacionSedeVirtualExamenForm(request.POST)
                form.edit(request.POST['supervisor'], request.POST['responsable'])
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if id != 0:
                    puede_realizar_accion(request, 'inno.puede_editar_planificacionexamenvirtual')
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    if AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(turnoplanificacion=eTurnoPlanificacionSedeVirtualExamen, aula=form.cleaned_data['aula']).exclude(pk=eAulaPlanificacionSedeVirtualExamen.pk).exists():
                        raise NameError(f"Aula ya se encuentra planificada en el horaro {eTurnoPlanificacionSedeVirtualExamen.horainicio.__str__()} a {eTurnoPlanificacionSedeVirtualExamen.horafin.__str__()} en la fecha {eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion.fecha.__str__()}")
                    eAulaPlanificacionSedeVirtualExamen.aula=form.cleaned_data['aula']
                    eAulaPlanificacionSedeVirtualExamen.responsable=form.cleaned_data['responsable']
                    eAulaPlanificacionSedeVirtualExamen.supervisor=form.cleaned_data['supervisor']
                    eAulaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Edito aula de planificación de examen virtual: %s' % eAulaPlanificacionSedeVirtualExamen, request, 'edit')
                else:
                    puede_realizar_accion(request, 'inno.puede_crear_planificacionexamenvirtual')
                    if AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(turnoplanificacion=eTurnoPlanificacionSedeVirtualExamen, aula=form.cleaned_data['aula']).exists():
                        raise NameError(f"Aula ya se encuentra planificada en el horaro {eTurnoPlanificacionSedeVirtualExamen.horainicio.__str__()} a {eTurnoPlanificacionSedeVirtualExamen.horafin.__str__()} en la fecha {eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion.fecha.__str__()}")
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen(turnoplanificacion=eTurnoPlanificacionSedeVirtualExamen,
                                                                                             aula=form.cleaned_data['aula'],
                                                                                             responsable=form.cleaned_data['responsable'],
                                                                                             supervisor=form.cleaned_data['supervisor'])
                    eAulaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Adiciono aula de planificación de examen virtual: %s' % eAulaPlanificacionSedeVirtualExamen, request, 'add')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteAulaPlanificacion':
            try:
                puede_realizar_accion(request, 'inno.puede_eliminar_planificacionexamenvirtual')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro a eliminar")
                eAulaPlanificacionSedeVirtualExamen = deleteAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                eAulaPlanificacionSedeVirtualExamen.delete()
                log(u'Elimino aula de planificación de examen virtual: %s' % deleteAulaPlanificacionSedeVirtualExamen, request, 'del')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'asignarAlumnoPlanificaciónExamen':
            try:
                if not 'idma' in request.POST:
                    raise NameError(u"No se encontro el parametro de materiaasignada")
                if not 'ida' in request.POST:
                    raise NameError(u"No se encontro el parametro de aula")
                idma = int(encrypt(request.POST['idma']))
                if not MateriaAsignada.objects.values("id").filter(pk=idma):
                    raise NameError(u"No se encontro la materia asignada")
                ida = int(encrypt(request.POST['ida']))
                if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=ida):
                    raise NameError(u"No se encontro el aula")
                iddme = int(encrypt(request.POST['iddme']))
                if not DetalleModeloEvaluativo.objects.values("id").filter(pk=iddme):
                    raise NameError(u"No se encontro el detalle del modelo evaluativo")
                eMateriaAsignada = MateriaAsignada.objects.get(pk=idma)
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=ida)
                eDetalleModeloEvaluativo = DetalleModeloEvaluativo.objects.get(pk=iddme)
                capacidad = eAulaPlanificacionSedeVirtualExamen.aula.capacidad
                cantidadad_planificadas = eAulaPlanificacionSedeVirtualExamen.cantidadad_planificadas()
                if cantidadad_planificadas + 1 > capacidad:
                    raise NameError(f"Capacidad llena, aula no permite más capacidad ({capacidad})")
                eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                if MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(materiaasignada=eMateriaAsignada, detallemodeloevaluativo=eDetalleModeloEvaluativo, aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo).exists():
                    raise NameError(f"Materia {eMateriaAsignada.materia.asignatura.nombre} del alumno {eMateriaAsignada.matricula.inscripcion.persona.__str__()} ya se encuentra planificada")
                filter_conflicto = Q(status=True)
                utilizar_qr = False
                if not eSedeVirtual.id == 11:
                    utilizar_qr = True
                    filter_conflicto = (Q(aulaplanificacion__turnoplanificacion__horainicio__lte=eTurnoPlanificacionSedeVirtualExamen.horafin,
                                          aulaplanificacion__turnoplanificacion__horafin__gte=eTurnoPlanificacionSedeVirtualExamen.horafin,
                                          aulaplanificacion__turnoplanificacion__fechaplanificacion__fecha=eFechaPlanificacionSedeVirtualExamen.fecha) |
                                        Q(aulaplanificacion__turnoplanificacion__horainicio__lte=eTurnoPlanificacionSedeVirtualExamen.horainicio,
                                          aulaplanificacion__turnoplanificacion__horafin__gte=eTurnoPlanificacionSedeVirtualExamen.horainicio,
                                          aulaplanificacion__turnoplanificacion__fechaplanificacion__fecha=eFechaPlanificacionSedeVirtualExamen.fecha))
                    if MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(filter_conflicto, materiaasignada__matricula=eMateriaAsignada.matricula, detallemodeloevaluativo=eDetalleModeloEvaluativo, aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo).exists():
                        raise NameError(f"El alumno {eMateriaAsignada.matricula.inscripcion.persona.__str__()} ya se encuentra planificado en la fecha y hora con otra materia")

                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen(materiaasignada=eMateriaAsignada,
                                                                                                               aulaplanificacion=eAulaPlanificacionSedeVirtualExamen,
                                                                                                               detallemodeloevaluativo=eDetalleModeloEvaluativo,
                                                                                                               utilizar_qr=utilizar_qr
                                                                                                               )
                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                log(u'Agrego materiaasignada a la planificación de examen virtual: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'add')
                return JsonResponse({"result": True, 'message': 'Se adiciono correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteMateriaAsignadaPlanificacion':
            try:
                puede_realizar_accion(request, 'inno.puede_eliminar_planificacionexamenvirtual')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro a eliminar")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = deleteMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                eMateriaAsignadaPlanificacionSedeVirtualExamen.delete()
                log(u'Elimino materiaasignada de planificación de examen virtual: %s' % deleteMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'del')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'generatePasswordAulaPlanificacion':
            try:
                puede_realizar_accion(request, 'inno.puede_editar_planificacionexamenvirtual')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro aula planificación")
                if not 'edicion' in request.POST:
                    raise NameError(u"No se encontro el parametro de edición")
                if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro aula planificación")
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                if request.POST['edicion'] == 'new':
                    eAulaPlanificacionSedeVirtualExamen.create_update_password()
                    eAulaPlanificacionSedeVirtualExamen.save(request)
                    password = eAulaPlanificacionSedeVirtualExamen.password
                    for eMateriaAsignadaPlanificacionSedeVirtualExamen in eAulaPlanificacionSedeVirtualExamen.materiaasignadaplanificadas():
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Generó una contraseña al aula de planificación de examen virtual: %s' % eAulaPlanificacionSedeVirtualExamen, request, 'add')
                else:
                    password = generar_clave_aleatoria(10)
                    eAulaPlanificacionSedeVirtualExamen.password = password
                    eAulaPlanificacionSedeVirtualExamen.save(request)
                    for eMateriaAsignadaPlanificacionSedeVirtualExamen in eAulaPlanificacionSedeVirtualExamen.materiaasignadaplanificadas():
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Se cambio la contraseña al aula de planificación de examen virtual: %s' % eAulaPlanificacionSedeVirtualExamen, request, 'edit')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'generatePasswordMateriaAsignadaPlanificacion':
            try:
                puede_realizar_accion(request, 'inno.puede_editar_planificacionexamenvirtual')
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro materia asignada planificación")
                if not 'edicion' in request.POST:
                    raise NameError(u"No se encontro el parametro de edición")
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro materia asignada planificación")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                if request.POST['edicion'] == 'new':
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.create_update_password()
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Generó una contraseña a la materia asignada de planificación de examen virtual: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'add')
                else:
                    password = generar_clave_aleatoria(10)
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request, updatePassword=True)
                    log(u'Se cambio la contraseña a la materia asignada de planificación de examen virtual: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'edit')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        return JsonResponse({"result": "bad", "message": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'resumensedes':
                try:
                    from sga.models import Coordinacion
                    data['title'] = u"Resumen de examenes en sedes"
                    return render(request, "adm_horarios/resumen_sedes/view.html", data)
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'sedesprovincias':
                try:
                    data['title'] = u'Sedes y Provincias Disponibles para Examenes'
                    data['sedesprovincias'] = SedeProvincia.objects.all()
                    return render(request, "adm_horarios/sedes_provincias/sedes_provincias.html", data)
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'adicionarelacion':
                try:
                    data['form']= SedeProvinciasForm()
                    return render(request,"adm_horarios/sedes_provincias/adicionar_sede_provincia.html", data)
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'editsede':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    sede_provincia = SedeProvincia.objects.get(pk=id)
                    initial_data = {
                        'sede_virtual': sede_provincia.sede_virtual,
                        'provincias': sede_provincia.provincia
                    }
                    data['form'] = SedeProvinciasForm(initial=initial_data)
                    template = get_template("adm_horarios/sedes_provincias/editar_sede_provincia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'deletesede':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['seleccionsedeprovincia'] = SedeProvincia.objects.get(pk=id)
                    template = get_template("adm_horarios/sedes_provincias/eliminar_sede_provincia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'maintenancecampus':
                try:
                    data['title'] = u'Mantenimiento de sedes'
                    search = None
                    ids = None
                    url_vars = ''
                    eSedes = SedeVirtual.objects.filter(status=True)
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        eSedes = eSedes.filter(id=ids)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        eSedes = eSedes.filter(Q(nombre__icontains=search)).distinct()
                        url_vars += '&s=' + search
                    paging = MiPaginador(eSedes, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data["url_params"] = url_vars
                    data['eSedes'] = page.object_list
                    return render(request, "adm_horarios/mantenimiento/sedes/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'loadFormSedeVirtual':
                try:
                    data['idForm'] = 'formSedeVirtual'
                    data['action'] = 'saveCampusVirtual'
                    id = 0
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET['id']))
                    if id != 0:
                        if not SedeVirtual.objects.values("id").filter(pk=id).exists():
                            raise NameError(f"No se encontro sede a editar")
                        eSedeVirtual = SedeVirtual.objects.get(pk=id)
                        form = SedeVirtualForm(initial=model_to_dict(eSedeVirtual))
                        data['id'] = encrypt(eSedeVirtual.id)
                    else:
                        form = SedeVirtualForm()
                        data['id'] = encrypt(0)
                    data['form'] = form
                    template = get_template("adm_horarios/mantenimiento/sedes/form.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'loadFormPeriodo':
                try:
                    data['idForm'] = 'formSedeVirtual'
                    data['action'] = 'saveCampusVirtualPeriodo'
                    form = SedeVirtualPeriodoForm()
                    data['id'] = int(encrypt(request.GET['id']))
                    data['form'] = form
                    template = get_template("adm_horarios/mantenimiento/sedes/form.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'maintenanceclassrooms':
                try:
                    data['title'] = u'Mantenimiento de aulas'
                    search = None
                    url_vars = ''
                    ids = 0
                    eSedeVirtuales = SedeVirtual.objects.filter(status=True, activa=True)
                    eLaboratorioVirtuales = LaboratorioVirtual.objects.filter(status=True)
                    if 'id' in request.GET:
                        id = request.GET['id']
                        eLaboratorioVirtuales = eLaboratorioVirtuales.filter(id=id)

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        eLaboratorioVirtuales = eLaboratorioVirtuales.filter(Q(nombre__icontains=search)).distinct()
                        url_vars += f'&s={search}'
                    if 'ids' in request.GET and encrypt(request.GET['ids']):
                        data['ids'] = ids = int(encrypt(request.GET['ids']))
                        eLaboratorioVirtuales = eLaboratorioVirtuales.filter(sedevirtual_id=ids)
                        url_vars += f'&ids={request.GET["ids"]}'
                    paging = MiPaginador(eLaboratorioVirtuales, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data['eLaboratorioVirtuales'] = page.object_list
                    data['eSedeVirtuales'] = eSedeVirtuales
                    return render(request, "adm_horarios/mantenimiento/aulas/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'loadFormAulaVirtual':
                try:
                    data['idForm'] = 'formAulaVirtual'
                    data['action'] = 'saveAulaVirtual'
                    id = 0
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET['id']))
                    if id != 0:
                        if not LaboratorioVirtual.objects.values("id").filter(pk=id).exists():
                            raise NameError(f"No se encontro sede a editar")
                        eLaboratorioVirtual = LaboratorioVirtual.objects.get(pk=id)
                        form = LaboratorioVirtualForm(initial=model_to_dict(eLaboratorioVirtual))
                        data['id'] = encrypt(eLaboratorioVirtual.id)
                    else:
                        form = LaboratorioVirtualForm()
                        data['id'] = encrypt(0)
                    data['form'] = form
                    template = get_template("adm_horarios/mantenimiento/aulas/form.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'loadFormFechaPlanificacion':
                try:
                    data['idForm'] = 'formFechaPlanificacion'
                    data['action'] = 'saveFechaPlanificacion'
                    id = 0
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET['id']))
                    if not 'ids' in request.GET:
                        raise NameError(f"No se encontro parametro de sede")
                    ids = int(encrypt(request.GET['ids']))
                    if not SedeVirtual.objects.values("id").filter(pk=ids).exists():
                        raise NameError(f"No se encontro sede")
                    data['ids'] = encrypt(ids)
                    if id != 0:
                        if not FechaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=id).exists():
                            raise NameError(f"No se encontro sede a editar")
                        eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                        form = FechaPlanificacionSedeVirtualExamenForm(initial=model_to_dict(eFechaPlanificacionSedeVirtualExamen))
                        if eFechaPlanificacionSedeVirtualExamen.supervisor:
                            form.edit(eFechaPlanificacionSedeVirtualExamen.supervisor.pk)
                        data['id'] = encrypt(eFechaPlanificacionSedeVirtualExamen.id)
                    else:
                        form = FechaPlanificacionSedeVirtualExamenForm(initial={'fecha': datetime.now().date()})
                        data['id'] = encrypt(0)

                    data['form'] = form
                    template = get_template("adm_horarios/examenes_sedes/fechaplanificacion/form.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'loadFormHorarioPlanificacion':
                try:
                    data['idForm'] = 'formHorarioPlanificacion'
                    data['action'] = 'saveHorarioPlanificacion'
                    id = 0
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET['id']))
                    if not 'idf' in request.GET:
                        raise NameError(f"No se encontro parametro de fecha")
                    idf = int(encrypt(request.GET['idf']))
                    if not FechaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=idf).exists():
                        raise NameError(f"No se encontro fecha")
                    data['idf'] = encrypt(idf)
                    if id != 0:
                        if not TurnoPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=id).exists():
                            raise NameError(f"No se encontro horario a editar")
                        eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=id)
                        form = HorarioPlanificacionSedeVirtualExamenForm(initial=model_to_dict(eTurnoPlanificacionSedeVirtualExamen))
                        data['id'] = encrypt(eTurnoPlanificacionSedeVirtualExamen.id)
                    else:
                        form = HorarioPlanificacionSedeVirtualExamenForm(initial={'horainicio': datetime.now().time(), 'horafin': datetime.now().time()})
                        data['id'] = encrypt(0)
                    data['form'] = form
                    template = get_template("adm_horarios/examenes_sedes/horarioplanificacion/form.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'loadFormAulaPlanificacion':
                try:
                    data['idForm'] = 'formAulaPlanificacion'
                    data['action'] = 'saveAulaPlanificacion'
                    id = 0
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET['id']))
                    if not 'idh' in request.GET:
                        raise NameError(f"No se encontro parametro de horario")
                    idh = int(encrypt(request.GET['idh']))
                    if not TurnoPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=idh).exists():
                        raise NameError(f"No se encontro horario")
                    data['idh'] = encrypt(idh)
                    eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                    eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    if id != 0:
                        if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=id).exists():
                            raise NameError(f"No se encontro aula a editar")
                        eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                        # eAulaPlanificacionSedeVirtualExamen.create_update_password()
                        form = AulaPlanificacionSedeVirtualExamenForm(initial=model_to_dict(eAulaPlanificacionSedeVirtualExamen))
                        form.edit(eAulaPlanificacionSedeVirtualExamen.supervisor.pk if eAulaPlanificacionSedeVirtualExamen.supervisor else None, eAulaPlanificacionSedeVirtualExamen.responsable.pk if eAulaPlanificacionSedeVirtualExamen.responsable else None)
                        data['id'] = encrypt(eAulaPlanificacionSedeVirtualExamen.id)
                        form.filter_sede(eSedeVirtual, list(AulaPlanificacionSedeVirtualExamen.objects.values_list("aula__id", flat=True).filter(turnoplanificacion=eTurnoPlanificacionSedeVirtualExamen).exclude(pk=eAulaPlanificacionSedeVirtualExamen.pk)))
                    else:
                        # form = AulaPlanificacionSedeVirtualExamenForm(initial={'password': generar_clave_aleatoria(10)})
                        form = AulaPlanificacionSedeVirtualExamenForm()
                        data['id'] = encrypt(0)
                        form.filter_sede(eSedeVirtual, list(AulaPlanificacionSedeVirtualExamen.objects.values_list("aula__id", flat=True).filter(turnoplanificacion=eTurnoPlanificacionSedeVirtualExamen)))
                    data['form'] = form
                    template = get_template("adm_horarios/examenes_sedes/aulaplanificacion/form.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'listAlumnoPlanificacionDataTable':
                try:
                    txt_filter = request.GET['sSearch'] if request.GET['sSearch'] else ''
                    limit = int(request.GET['iDisplayLength']) if request.GET['iDisplayLength'] else 25
                    offset = int(request.GET['iDisplayStart']) if request.GET['iDisplayStart'] else 0
                    id_aula = int(request.GET['id']) if request.GET['id'] else 0
                    aaData = []
                    tCount = 0
                    eMallaIngles = Malla.objects.filter(pk__in=[353, 22])
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id_aula)
                    eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    horainicio = eTurnoPlanificacionSedeVirtualExamen.horainicio
                    horafin = eTurnoPlanificacionSedeVirtualExamen.horafin
                    fecha = eFechaPlanificacionSedeVirtualExamen.fecha
                    ePeriodo = eFechaPlanificacionSedeVirtualExamen.periodo
                    # detallemodeloevaluativo_id = 0
                    # if periodo.es_pregrado():
                    #     detallemodeloevaluativo_id = [37, 123]
                    # elif periodo.es_admision():
                    #     detallemodeloevaluativo_id = [114]
                    # if detallemodeloevaluativo_id == 0:
                    #     raise NameError(u"No se encontro modelo evaluativo")
                    # eDetalleModeloEvaluativo = DetalleModeloEvaluativo.objects.filter(pk=detallemodeloevaluativo_id)
                    cursor = connections['sga_select'].cursor()
                    eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(status=True, matricula__status=True,
                                                                                matricula__retiradomatricula=False,
                                                                                matricula__nivel__periodo=ePeriodo).distinct()
                    eMatriculas = Matricula.objects.filter(pk__in=eMatriculaSedeExamenes.values_list("matricula__id", flat=True), status=True, retiradomatricula=False, bloqueomatricula=False, nivel__periodo=ePeriodo)
                    sql = f"""SELECT 
                                                        "sga_matricula"."id", 
                                                        COUNT("sga_materia"."asignaturamalla_id") 
                                                                FILTER (WHERE ("sga_asignaturamalla"."malla_id" NOT IN (SELECT U0."id"
                                                                                                                            FROM "sga_malla" U0
                                                                                                                            WHERE U0."id" IN (353, 22)
                                                                                                                        ) AND 
                                                                                "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                                                "sga_matricula"."status" AND 
                                                                                "sga_materia"."asignatura_id" NOT IN (4837)
                                                                                )
                                                                        ) AS "total_general", 
                                                        COUNT("sga_materia"."asignaturamalla_id") 
                                                                FILTER (WHERE ("sga_materiaasignada"."id" IN (	SELECT U0."materiaasignada_id"
                                                                                                                    FROM "inno_materiaasignadaplanificacionsedevirtualexamen" U0
                                                                                                                    INNER JOIN "sga_materiaasignada" U1 ON U1."id" = U0.materiaasignada_id
                                                                                                                    WHERE U1."matricula_id" = "sga_matricula"."id"
                                                                                                                ) AND
                                                                                "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                                                "sga_matricula"."status" AND 
                                                                                "sga_materia"."asignatura_id" NOT IN (4837))
                                                                        ) AS "total_planificadas"
                                                    FROM "sga_matricula"
                                                    INNER JOIN "sga_inscripcion" ON "sga_matricula"."inscripcion_id" = "sga_inscripcion"."id"
                                                    INNER JOIN "sga_inscripcionmalla" ON "sga_inscripcion"."id" = "sga_inscripcionmalla"."inscripcion_id"
                                                    INNER JOIN "sga_nivel" ON "sga_matricula"."nivel_id" = "sga_nivel"."id"
                                                    INNER JOIN "sga_periodo" ON "sga_nivel"."periodo_id" = "sga_periodo"."id"
                                                    LEFT OUTER JOIN "sga_materiaasignada" ON "sga_matricula"."id" = "sga_materiaasignada"."matricula_id"
                                                    LEFT OUTER JOIN "sga_materia" ON "sga_materiaasignada"."materia_id" = "sga_materia"."id"
                                                    LEFT OUTER JOIN "sga_asignaturamalla" ON "sga_materia"."asignaturamalla_id" = "sga_asignaturamalla"."id"
                                                    WHERE (
                                                        NOT "sga_matricula"."bloqueomatricula" AND 
                                                        "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                        "sga_matricula"."id" IN (
                                                                                            SELECT DISTINCT 
                                                                                                U0."matricula_id"
                                                                                            FROM "inno_matriculasedeexamen" U0
                                                                                                INNER JOIN "sga_matricula" U2 ON U0."matricula_id" = U2."id"
                                                                                                INNER JOIN "sga_nivel" U3 ON U2."nivel_id" = U3."id"
                                                                                            WHERE ( 
                                                                                                        U3."periodo_id" = {ePeriodo.pk} AND 
                                                                                                        NOT U2."retiradomatricula" AND 
                                                                                                        U2."status" AND 
                                                                                                        U0."sede_id" = {eSedeVirtual.pk} AND 
                                                                                                        U0."status"
                                                                                                    )
                                                                                        ) AND 
                                                        NOT "sga_matricula"."retiradomatricula" AND 
                                                        "sga_matricula"."status"
                                                        )
                                                    GROUP BY "sga_matricula"."id"
                                                    HAVING 
                                                            COUNT("sga_materia"."asignaturamalla_id") 
                                                                FILTER (WHERE ("sga_asignaturamalla"."malla_id" NOT IN (SELECT U0."id"
                                                                                                                            FROM "sga_malla" U0
                                                                                                                            WHERE U0."id" IN (353, 22)
                                                                                                                        ) AND 
                                                                                "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                                                "sga_matricula"."status" AND 
                                                                                "sga_materia"."asignatura_id" NOT IN (4837)
                                                                                )
                                                                        ) 
                                                            <> 
                                                            COUNT("sga_materia"."asignaturamalla_id") 
                                                                FILTER (WHERE ("sga_materiaasignada"."id" IN (SELECT U0."materiaasignada_id"
                                                                                                                FROM "inno_materiaasignadaplanificacionsedevirtualexamen" U0
                                                                                                                INNER JOIN "sga_materiaasignada" U1 ON U1."id" = U0.materiaasignada_id
                                                                                                                WHERE U1."matricula_id" = "sga_matricula"."id"
                                                                                                            ) AND
                                                                                "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                                                "sga_matricula"."status" AND 
                                                                                "sga_materia"."asignatura_id" NOT IN (4837))
                                                                        )"""
                    # cursor.execute(sql)
                    # results = cursor.fetchall()
                    # ids_matricula = [r[0] for r in results]
                    # eMatriculas = eMatriculas.filter(pk__in=ids_matricula)
                    if txt_filter:
                        search = txt_filter.strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            eMatriculas = eMatriculas.filter(Q(inscripcion__persona__cedula__icontains=search) |
                                                             Q(inscripcion__persona__pasaporte__icontains=search) |
                                                             Q(inscripcion__persona__ruc__icontains=search) |
                                                             Q(inscripcion__persona__nombres__icontains=search) |
                                                             Q(inscripcion__persona__apellido1__icontains=search) |
                                                             Q(inscripcion__persona__apellido2__icontains=search))
                        else:
                            eMatriculas = eMatriculas.filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                             Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                             Q(inscripcion__persona__apellido2__icontains=ss[1]))
                    tCount = len(eMatriculas)
                    if offset == 0:
                        rows = eMatriculas[offset:limit]
                    else:
                        rows = eMatriculas[offset:offset + limit]
                    aaData = []
                    for row in rows:
                        documento = row.inscripcion.persona.documento()
                        tipodocumento = row.inscripcion.persona.tipo_documento()
                        alumno = row.inscripcion.persona.nombre_completo_inverso()
                        sexo = row.inscripcion.persona.sexo
                        telefono = row.inscripcion.persona.telefono
                        email = row.inscripcion.persona.email
                        emailinst = row.inscripcion.persona.emailinst
                        carrera = row.inscripcion.carrera.__str__()
                        eMateriaAsignadas = row.materias_x_planificar_examen(ePeriodo, eSedeVirtual)
                        eMateriaAsignadaSerializer = []
                        contadorMateriaAsignada = 1
                        for eMateriaAsignada in eMateriaAsignadas:
                            eDetalleModeloEvaluativos = []
                            for eDetalleModeloEvaluativo in eMateriaAsignada.materia.modeloevaluativo.detallemodeloevaluativo_set.filter(status=True, alternativa__id__in=[20, 21, 30, 31, 14], modelo__status=True):
                                eDetalleModeloEvaluativos.append({"id": encrypt(eDetalleModeloEvaluativo.pk),
                                                                  "nombre": eDetalleModeloEvaluativo.nombre,
                                                                  "selected": False})
                            eMateriaAsignadaSerializer.append({"id": encrypt(eMateriaAsignada.pk),
                                                               "asignatura": eMateriaAsignada.materia.asignatura.nombre,
                                                               "nivel": eMateriaAsignada.materia.asignaturamalla.nivelmalla.nombre,
                                                               "num": contadorMateriaAsignada,
                                                               "matricula_id": encrypt(row.id),
                                                               "aula_id": encrypt(eAulaPlanificacionSedeVirtualExamen.pk),
                                                               "detallemodeloevaluativos": eDetalleModeloEvaluativos})
                            contadorMateriaAsignada +=1
                        aaData.append([{"type_document": tipodocumento,
                                        "document": documento,
                                        "nombre_completo": alumno,
                                        "sexo": sexo.nombre if sexo else '-',
                                        "telefono": telefono if telefono else '-',
                                        "email": email if email else '-',
                                        "emailinst": emailinst if emailinst else '-'
                                        },
                                       carrera,
                                       eMateriaAsignadaSerializer,
                                       ])
                    return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

            elif action == 'reportPlanificacionSedes':
                try:
                    if data['permiteWebPush']:
                        eNotificacion = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                                     titulo=f'Excel Planificación de sedes {periodo.get_clasificacion_display() if periodo.clasificacion else ""}'.strip(),
                                                     destinatario=persona,
                                                     url='',
                                                     prioridad=1,
                                                     app_label='SGA',
                                                     fecha_hora_visible=datetime.now() + timedelta(days=1),
                                                     tipo=2,
                                                     en_proceso=True)
                        eNotificacion.save(request)
                        ReportPlanificacionSedes(request=request, data=data, eNotificacion=eNotificacion).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        __author__ = 'Unemi'
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('hoja1')
                        ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write_merge(1, 1, 0, 9, 'REPORTE DE PLANIFICACIÓN DE SEDES', titulo2)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=reporte_planificación_sedes' + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"#", 1000),
                            (u"SEDE", 10000),
                            (u"FECHA", 6000),
                            (u"HORA INICIO", 6000),
                            (u"HORA FIN", 6000),
                            (u"SALA/LABORATORIO", 6000),
                            (u"CAPACIDAD", 6000),
                            (u"PLANIFICADOS", 6000),
                            (u"SUPERVISOR", 6000),
                            (u"APLICADOR", 6000),
                        ]
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        ePeriodo = periodo
                        eMaterias = Materia.objects.filter(nivel__periodo=ePeriodo, status=True).exclude(asignatura_id=4837)
                        eNiveles = Nivel.objects.filter(status=True, periodo=periodo, materia__isnull=False, id__in=eMaterias.values_list('nivel_id', flat=True)).distinct()
                        eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(status=True, matricula__status=True, matricula__retiradomatricula=False, matricula__nivel__in=eNiveles)
                        eSedes = SedeVirtual.objects.filter(pk__in=eMatriculaSedeExamenes.values_list('sede_id', flat=True))
                        eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(status=True,
                                                                                                                  turnoplanificacion__fechaplanificacion__periodo=ePeriodo,
                                                                                                                  turnoplanificacion__fechaplanificacion__sede__in=eSedes)
                        row_num = 4
                        i = 0
                        for eAulaPlanificacionSedeVirtualExamen in eAulaPlanificacionSedeVirtualExamenes:
                            i += 1
                            eLaboratorioVirtual = eAulaPlanificacionSedeVirtualExamen.aula
                            eAplicador = eAulaPlanificacionSedeVirtualExamen.responsable
                            eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                            eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                            eSupervisor = eFechaPlanificacionSedeVirtualExamen.supervisor
                            eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                            ws.write(row_num, 0, str(i), font_style2)
                            ws.write(row_num, 1, eSedeVirtual.nombre, font_style2)
                            ws.write(row_num, 2, eFechaPlanificacionSedeVirtualExamen.fecha.__str__(), font_style2)
                            ws.write(row_num, 3, eTurnoPlanificacionSedeVirtualExamen.horainicio.__str__(), font_style2)
                            ws.write(row_num, 4, eTurnoPlanificacionSedeVirtualExamen.horafin.__str__(), font_style2)
                            ws.write(row_num, 5, eLaboratorioVirtual.nombre, font_style2)
                            ws.write(row_num, 6, str(eLaboratorioVirtual.capacidad), font_style2)
                            ws.write(row_num, 7, str(eAulaPlanificacionSedeVirtualExamen.cantidadad_planificadas()), font_style2)
                            ws.write(row_num, 8, eSupervisor.nombre_completo() if eSupervisor else '', font_style2)
                            ws.write(row_num, 9, eAplicador.nombre_completo() if eAplicador else '', font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                except Exception as ex:
                    if data['permiteWebPush']:
                        return JsonResponse({"result": False, "mensaje": f"Error al generar reporte, {ex.__str__()}"})
                    else:
                        HttpResponseRedirect(f"{request.path}?info=Error al generar reporte, {ex.__str__()}")

            elif action == 'reportAlumnoHorarios':
                try:
                    if data['permiteWebPush']:
                        eNotificacion = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                                     titulo=f'Excel Horario de examenes en sedes {periodo.get_clasificacion_display() if periodo.clasificacion else ""}'.strip(),
                                                     destinatario=persona,
                                                     url='',
                                                     prioridad=1,
                                                     app_label='SGA',
                                                     fecha_hora_visible=datetime.now() + timedelta(days=1),
                                                     tipo=2,
                                                     en_proceso=True)
                        eNotificacion.save(request)
                        ReportHorariosExamenesSedes(request=request, data=data, eNotificacion=eNotificacion).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        __author__ = 'Unemi'
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('hoja1')
                        ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write_merge(1, 1, 0, 15, 'REPORTE DE HORARIOS DE EXÁMENES DE ALUMNOS EN SEDES', titulo2)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=reporte_horarios_examenes_sedes' + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"#", 1000),
                            (u"TIPO DOCUMENTO", 10000),
                            (u"DOCUMENTO", 10000),
                            (u"ALUMNO", 10000),
                            (u"CARRERA", 10000),
                            (u"MODALIDAD", 10000),
                            (u"NIVEL", 10000),
                            (u"ASIGNATURA", 10000),
                            (u"SEDE", 10000),
                            (u"FECHA", 6000),
                            (u"HORA INICIO", 6000),
                            (u"HORA FIN", 6000),
                            (u"SALA/LABORATORIO", 6000),
                            (u"SUPERVISOR", 6000),
                            (u"APLICADOR", 6000),
                            (u"NUM. PLANIFICACIÓN", 6000),
                        ]
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        ePeriodo = periodo
                        eMaterias = Materia.objects.filter(nivel__periodo=ePeriodo, status=True).exclude(asignatura_id=4837)
                        eMateriaAsignadas = MateriaAsignada.objects.filter(materia__in=eMaterias, matricula__status=True, matricula__bloqueomatricula=False, retiramateria=False, status=True).order_by('matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres').distinct()
                        row_num = 4
                        i = 0
                        for eMateriaAsignada in eMateriaAsignadas:
                            i += 1
                            eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada=eMateriaAsignada)
                            eMateria = eMateriaAsignada.materia
                            eAsignaturaMalla = eMateria.asignaturamalla
                            eNivelMalla = eAsignaturaMalla.nivelmalla
                            eAsignatura = eAsignaturaMalla.asignatura
                            eMatricula = eMateriaAsignada.matricula
                            eInscripcion = eMatricula.inscripcion
                            eModalidad = eInscripcion.modalidad
                            eCarrera = eInscripcion.carrera
                            ePersona = eInscripcion.persona
                            eLaboratorioVirtual = None
                            eAplicador = None
                            eSupervisor = None
                            eTurnoPlanificacionSedeVirtualExamen = None
                            eFechaPlanificacionSedeVirtualExamen = None
                            eSedeVirtual = None
                            if eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").exists():
                                eMateriaAsignadaPlanificacionSedeVirtualExamen = eMateriaAsignadaPlanificacionSedeVirtualExamenes.first()
                                eAulaPlanificacionSedeVirtualExamen = eMateriaAsignadaPlanificacionSedeVirtualExamen.aulaplanificacion
                                eLaboratorioVirtual = eAulaPlanificacionSedeVirtualExamen.aula
                                eAplicador = eAulaPlanificacionSedeVirtualExamen.responsable
                                eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                                eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                                eSupervisor = eFechaPlanificacionSedeVirtualExamen.supervisor
                                eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                            if not eSedeVirtual:
                                eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(matricula=eMateriaAsignada.matricula, status=True)
                                if eMatriculaSedeExamenes.values("id").exists():
                                    eMatriculaSedeExamen = eMatriculaSedeExamenes.first()
                                    eSedeVirtual = eMatriculaSedeExamen.sede
                            ws.write(row_num, 0, str(i), font_style2)
                            ws.write(row_num, 1, ePersona.tipo_documento(), font_style2)
                            ws.write(row_num, 2, ePersona.documento(), font_style2)
                            ws.write(row_num, 3, ePersona.nombre_completo(), font_style2)
                            ws.write(row_num, 4, eCarrera.nombrevisualizar if eCarrera.nombrevisualizar else eCarrera.nombre, font_style2)
                            ws.write(row_num, 5, eModalidad.nombre if eModalidad else '', font_style2)
                            ws.write(row_num, 6, eNivelMalla.nombre, font_style2)
                            ws.write(row_num, 7, eAsignatura.nombre, font_style2)
                            ws.write(row_num, 8, eSedeVirtual.nombre if eSedeVirtual else '', font_style2)
                            ws.write(row_num, 9, eFechaPlanificacionSedeVirtualExamen.fecha.__str__() if eFechaPlanificacionSedeVirtualExamen else '', font_style2)
                            ws.write(row_num, 10, eTurnoPlanificacionSedeVirtualExamen.horainicio.__str__() if eTurnoPlanificacionSedeVirtualExamen else '', font_style2)
                            ws.write(row_num, 11, eTurnoPlanificacionSedeVirtualExamen.horafin.__str__() if eTurnoPlanificacionSedeVirtualExamen else '', font_style2)
                            ws.write(row_num, 12, eLaboratorioVirtual.nombre if eLaboratorioVirtual else '', font_style2)
                            ws.write(row_num, 13, eSupervisor.nombre_completo() if eSupervisor else '', font_style2)
                            ws.write(row_num, 14, eAplicador.nombre_completo() if eAplicador else '', font_style2)
                            ws.write(row_num, 15, len(eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id")), font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                except Exception as ex:
                    if data['permiteWebPush']:
                        return JsonResponse({"result": False, "mensaje": f"Error al generar reporte, {ex.__str__()}"})
                    else:
                        HttpResponseRedirect(f"{request.path}?info=Error al generar reporte, {ex.__str__()}")

            elif action == 'reportAlumnoHorariosNoExamen':
                try:
                    eNotificacion = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                                 titulo=f'Excel de personas que no rindieron exámen {periodo.get_clasificacion_display() if periodo.clasificacion else ""}'.strip(),
                                                 destinatario=persona,
                                                 url='',
                                                 prioridad=1,
                                                 app_label='SGA',
                                                 fecha_hora_visible=datetime.now() + timedelta(days=1),
                                                 tipo=2,
                                                 en_proceso=True)
                    eNotificacion.save(request)
                    reporte_persona_sin_examen(request=request, data=data, notif=eNotificacion).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Error al generar reporte, {ex.__str__()}"})

            elif action == 'reportPlanificacionExamen':
                try:
                    eNotificacion = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                                 titulo=f'Planificación de examenes',
                                                 destinatario=persona,
                                                 url='',
                                                 prioridad=1,
                                                 app_label='SGA',
                                                 fecha_hora_visible=datetime.now() + timedelta(days=1),
                                                 tipo=2,
                                                 en_proceso=True)
                    eNotificacion.save(request)
                    ReportPlanificacionExamenes(request=request, data=data, notif=eNotificacion).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Error al generar reporte, {ex.__str__()}"})

            elif action == 'searchPersonas':
                try:
                    q = request.GET['q'].upper().strip()
                    ePersonas = Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False))
                    search = q.strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        ePersonas = ePersonas.filter(Q(cedula__icontains=search) |
                                                     Q(pasaporte__icontains=search) |
                                                     Q(nombres__icontains=search) |
                                                     Q(apellido1__icontains=search) |
                                                     Q(apellido2__icontains=search))
                    else:
                        ePersonas = ePersonas.filter(Q(nombres__icontains=search) |
                                                     Q(apellido1__icontains=ss[0]) &
                                                     Q(apellido2__icontains=ss[1]))
                    ePersonas = ePersonas.distinct().order_by('apellido1', 'apellido2', 'nombres')[:15]
                    aData = {"results": [{"id": x.id, "name": "({}) - {}".format(x.documento(), x.nombre_completo())} for x in ePersonas]}
                    return JsonResponse({"result": True, 'mensaje': '', 'aData': aData})
                except Exception as ex:
                    return JsonResponse({"result": True, 'mensaje': f'{ex.__str__()}', 'aData': {"results": []}})

            return HttpResponseRedirect(request.path)
        else:
            try:
                if 'info' in request.GET:
                    data['info'] = request.GET['info']
                data['title'] = u'Administración de horarios de exámenes en sedes'
                data['ePeriodo'] = periodo
                data_json = {
                    'periodo_id': periodo.id,
                }
                eMatriculas = Matricula.objects.filter(status=True, retiradomatricula=False, inscripcion__modalidad_id__lte=3, nivel__periodo=periodo)
                # eMaterias = Materia.objects.filter(nivel__periodo=periodo, asignaturamalla__malla__modalidad_id__lte=3, status=True)
                # eNiveles = Nivel.objects.filter(periodo=periodo, materia__isnull=False, id__in=eMaterias.values_list('nivel_id', flat=True)).distinct()
                # eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(status=True, matricula__status=True, matricula__retiradomatricula=False, matricula__nivel__in=eNiveles, matricula__inscripcion__modalidad_id=3, matricula__id__in=eMatriculas.values("id").distinct())
                eSedes = SedeVirtual.objects.filter(sedevirtualperiodoacademico__periodo=periodo, sedevirtualperiodoacademico__status=True, status=True,activa=True)
                data['eSedes'] = SedeVirtualSerializer(eSedes, many=True, context=data_json).data if eSedes.values("id").exists() else []
                if 'ids' in request.GET:
                    ids = int(encrypt(request.GET['ids']))
                    eSedeVirtual = SedeVirtual.objects.get(pk=ids)
                    data_json['isView_FechaPlanificacion'] = True
                    eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context=data_json).data
                    data['eSede'] = eSedeSerializer
                    return render(request, "adm_horarios/examenes_sedes/sedevirtual/view.html", data)
                if 'idf' in request.GET:
                    idf = int(encrypt(request.GET['idf']))
                    eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=idf)
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    # data_json['isView_FechaPlanificacion'] = True
                    eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context={'periodo_id': periodo.id, 'isView_FechaPlanificacion': True}).data
                    eFechaPlanificacionSedeVirtualExamenSerializer = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamen, context={'periodo_id': periodo.id, 'isView_HoraPlanificacion': True}).data
                    data['eSede'] = eSedeSerializer
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamenSerializer
                    return render(request, "adm_horarios/examenes_sedes/fechaplanificacion/view.html", data)
                if 'idh' in request.GET:
                    idh = int(encrypt(request.GET['idh']))
                    eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                    eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context={'periodo_id': periodo.id, 'isView_FechaPlanificacion': True, 'isView_HoraPlanificacion': True}).data
                    eFechaPlanificacionSedeVirtualExamenSerializer = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamen, context=data_json).data
                    eTurnoPlanificacionSedeVirtualExamenSerializer = TurnoPlanificacionSedeVirtualExamenSerializer(eTurnoPlanificacionSedeVirtualExamen, context={'periodo_id': periodo.id, 'isView_AulaPlanificacion': True}).data
                    data['eSede'] = eSedeSerializer
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamenSerializer
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamenSerializer
                    return render(request, "adm_horarios/examenes_sedes/horarioplanificacion/view.html", data)
                if 'ida' in request.GET:
                    ida = int(encrypt(request.GET['ida']))
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=ida)
                    eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context={'periodo_id': periodo.id, 'isView_FechaPlanificacion': True, 'isView_HoraPlanificacion': True, 'isView_AulaPlanificacion': True}).data
                    eFechaPlanificacionSedeVirtualExamenSerializer = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamen, context=data_json).data
                    eTurnoPlanificacionSedeVirtualExamenSerializer = TurnoPlanificacionSedeVirtualExamenSerializer(eTurnoPlanificacionSedeVirtualExamen, context=data_json).data
                    eAulaPlanificacionSedeVirtualExamenSerializer = AulaPlanificacionSedeVirtualExamenSerializer(eAulaPlanificacionSedeVirtualExamen, context=data_json).data
                    data['eSede'] = eSedeSerializer
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamenSerializer
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamenSerializer
                    data['eAulaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamenSerializer
                    data['eResponsable'] = PersonaSerializer(eAulaPlanificacionSedeVirtualExamen.responsable).data if eAulaPlanificacionSedeVirtualExamen.responsable else None
                    search = None
                    url_vars = ''
                    eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion=eAulaPlanificacionSedeVirtualExamen, status=True)
                    if 'id' in request.GET:
                        id = request.GET['id']
                        eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(id=id)

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__cedula__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__pasaporte__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__usuario__username__icontains=search)).distinct().select_related('materiaasignada__matricula__inscripcion__persona')
                        else:
                            eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1])).distinct().select_related('materiaasignada__matricula__inscripcion__persona')
                        url_vars += f'&s={search}'
                    # eMateriaAsignadaPlanificacionSedeVirtualExamenSerializer = MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamenes, many=True).data if eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").exists() else []
                    paging = MiPaginador(eMateriaAsignadaPlanificacionSedeVirtualExamenes, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data['eMateriaAsignadaPlanificacionSedeVirtualExamenes'] = page.object_list
                    return render(request, "adm_horarios/examenes_sedes/aulaplanificacion/view.html", data)
                infoMatriculados = {'matriculados': len(eMatriculas.values_list("id", flat=True)),
                                    'asignados': 0,
                                    'x_asignar': len(eMatriculas.values_list("id", flat=True)) - 0}
                data['infoMatriculados'] = infoMatriculados
                # tablaExamenSedes = []
                # eMallasIngles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
                # eMateriaAsignadas = MateriaAsignada.objects.filter(matricula__id__in=eMatriculas.values_list("id", flat=True), status=True, retiramateria=False)
                # eMateriaAsignadas = eMateriaAsignadas.exclude(Q(materia__asignaturamalla__malla_id__in=eMallasIngles.values_list("id", flat=True)) |
                #                                               Q(materia__asignatura__id=4837))
                # totalPlanificados = eMateriaAsignadas.count()
                # eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo, status=True)
                # eSedes = eSedes.filter(pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes.values_list('aulaplanificacion__turnoplanificacion__fechaplanificacion__sede__id', flat=True))
                # for eSede in eSedes:
                #     eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo, status=True,
                #                                                                                                                     aulaplanificacion__turnoplanificacion__fechaplanificacion__sede=eSede)
                #     eMateriaAsignadas = eMateriaAsignadas.filter(pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes.values_list("materiaasignada__id", flat=True),
                #                                                  status=True, retiramateria=False)
                #     eMateriaAsignadas = eMateriaAsignadas.exclude(Q(materia__asignaturamalla__malla_id__in=eMallasIngles.values_list("id", flat=True)) |
                #                                                   Q(materia__asignatura__id=4837))
                #     porcentaje = round(((eMateriaAsignadas.count() * 100) / totalPlanificados), 2)
                #     tablaExamenSedes.append({"sede": eSede.nombre,
                #                              "porcentaje": porcentaje,
                #                              "total_sede": eMateriaAsignadas.count()})
                # eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo,
                #                                                                                                                 status=True, aulaplanificacion__turnoplanificacion__fechaplanificacion__sede__in=eSedes)
                # eMateriaAsignadas = MateriaAsignada.objects.filter(matricula__id__in=eMatriculas.values_list("id", flat=True), status=True, retiramateria=False)
                # eMateriaAsignadas = eMateriaAsignadas.exclude(Q(materia__asignaturamalla__malla_id__in=eMallasIngles.values_list("id", flat=True)) |
                #                                               Q(materia__asignatura__id=4837) |
                #                                               Q(pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes.values_list("materiaasignada__id", flat=True)))
                # if eMateriaAsignadas.values("id").exists():
                #     porcentaje = round(((eMateriaAsignadas.count() * 100) / totalPlanificados), 2)
                #     tablaExamenSedes.append({"sede": "Sin sede de asignación",
                #                                   "porcentaje": porcentaje,
                #                                   "total_sede": eMateriaAsignadas.count()})
                # data['tablaExamenSedes'] = tablaExamenSedes
                # data['totalPlanificados'] = totalPlanificados
                return render(request, "adm_horarios/examenes_sedes/panel.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_horarios/error.html", data)
