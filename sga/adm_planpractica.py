# -*- coding: UTF-8 -*-
import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template import Context
import xlwt
from xlwt import *
from decorators import secure_module
from sga.forms import *
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import *
from sga.funciones import MiPaginador, log, generar_nombre, fechaletra_corta, get_director_vinculacion, \
    remover_caracteres_tildes_unicode
from django.forms import model_to_dict
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdf_name
from sga.templatetags.sga_extras import encrypt, calcular_tiempo_cumplimiento
from django.db.models import Q, Sum, Count, Max, F, Avg
from django.db.models.functions import Cast
from django.db.models import FloatField

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    hoy = datetime.now()
    responsablevinculacion = get_director_vinculacion()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'practicas':
            try:
                convenio = AcuerdoCompromiso.objects.get(pk=request.POST['idconvenio'])
                if convenio.para_practicas:
                    convenio.para_practicas = False
                else:
                    convenio.para_practicas = True
                convenio.save(request)
                return JsonResponse({'result': 'ok', 'valor': convenio.para_practicas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pasantias':
            try:
                convenio = AcuerdoCompromiso.objects.get(pk=request.POST['idconvenio'])
                if convenio.para_pasantias:
                    convenio.para_pasantias = False
                else:
                    convenio.para_pasantias = True
                convenio.save(request)
                return JsonResponse({'result': 'ok', 'valor': convenio.para_pasantias})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'add':
            try:
                if 'archivocomisiongestionacademica' in request.FILES:
                    d = request.FILES['archivocomisiongestionacademica']
                    if d.size > 2621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                    else:
                        newfiles = request.FILES['archivocomisiongestionacademica']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf .PDF"})
                f = PlanPracticaPreProfesionalForm(request.POST)
                if f.is_valid():
                    newfile = None
                    if 'archivocomisiongestionacademica' in request.FILES:
                        newfile = request.FILES['archivocomisiongestionacademica']
                        newfile._name = generar_nombre("archivocomisiongestionacademica_", newfile._name)
                    plan = PlanPracticaPreProfesional(objetivo=f.cleaned_data['objetivo'],
                                                      fechadesde=f.cleaned_data['fechadesde'],
                                                      fechahasta=f.cleaned_data['fechahasta'],
                                                      comisiongestionacademica=f.cleaned_data[
                                                          'comisiongestionacademica'],
                                                      archivocomisiongestionacademica=newfile,
                                                      )
                    plan.save(request)
                    log(u'Adiciono nuevo plan: %s' % plan, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                if 'archivocomisiongestionacademica' in request.FILES:
                    d = request.FILES['archivocomisiongestionacademica']
                    if d.size > 2621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                    else:
                        newfiles = request.FILES['archivocomisiongestionacademica']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                plan = PlanPracticaPreProfesional.objects.get(pk=int(encrypt(request.POST['id'])))
                f = PlanPracticaPreProfesionalForm(request.POST)
                if f.is_valid():
                    newfile = None
                    if 'archivocomisiongestionacademica' in request.FILES:
                        newfile = request.FILES['archivocomisiongestionacademica']
                        newfile._name = generar_nombre("archivocomisiongestionacademica_", newfile._name)
                    plan.objetivo = f.cleaned_data['objetivo']
                    plan.fechadesde = f.cleaned_data['fechadesde']
                    plan.fechahasta = f.cleaned_data['fechahasta']
                    plan.comisiongestionacademica = f.cleaned_data['comisiongestionacademica']
                    if newfile:
                        plan.archivocomisiongestionacademica = newfile
                    plan.save(request)
                    log(u'Modificó plan: %s' % plan, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                plan = PlanPracticaPreProfesional.objects.get(pk=int(encrypt(request.POST['id'])))
                # if plan.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"El plan se encuentra en uso, no es posible eliminar."})
                log(u'Eliminó plan: %s' % plan, request, "del")
                plan.status = False
                plan.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addprograma':
            try:
                if 'archivoconsejodirectivo' in request.FILES:
                    d = request.FILES['archivoconsejodirectivo']
                    if d.size > 2621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                    else:
                        newfiles = request.FILES['archivoconsejodirectivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                if 'archivocomisiongestionacademica' in request.FILES:
                    d = request.FILES['archivocomisiongestionacademica']
                    if d.size > 10621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    else:
                        newfiles = request.FILES['archivocomisiongestionacademica']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = ProgramaPracticaPreProfesionalForm(request.POST)
                if f.is_valid():
                    plan = PlanPracticaPreProfesional.objects.get(id=int(encrypt(request.POST['idp'])))
                    newfile = None
                    if 'archivoconsejodirectivo' in request.FILES:
                        newfile = request.FILES['archivoconsejodirectivo']
                        newfile._name = generar_nombre("archivoconsejodirectivo_", newfile._name)
                    newfile1 = None
                    if 'archivocomisiongestionacademica' in request.FILES:
                        newfile1 = request.FILES['archivocomisiongestionacademica']
                        newfile1._name = generar_nombre("archivocomisiongestionacademica_", newfile._name)
                    programa = ProgramaPracticaPreProfesional(plan=plan,
                                                              objetivo=f.cleaned_data['objetivo'],
                                                              carrera=f.cleaned_data['carrera'],
                                                              fechadesde=f.cleaned_data['fechadesde'],
                                                              fechahasta=f.cleaned_data['fechahasta'],
                                                              comisiongestionacademica=f.cleaned_data[
                                                                  'comisiongestionacademica'],
                                                              consejodirectivo=f.cleaned_data['consejodirectivo'],
                                                              archivoconsejodirectivo=newfile,
                                                              archivocomisiongestionacademica=newfile1,
                                                              )
                    programa.save(request)
                    log(u'Adiciono nuevo programa: %s' % programa, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editprograma':
            try:
                if 'archivoconsejodirectivo' in request.FILES:
                    d = request.FILES['archivoconsejodirectivo']
                    if d.size > 10621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    else:
                        newfiles = request.FILES['archivoconsejodirectivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                if 'archivocomisiongestionacademica' in request.FILES:
                    d = request.FILES['archivocomisiongestionacademica']
                    if d.size > 10621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    else:
                        newfiles = request.FILES['archivocomisiongestionacademica']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                programa = ProgramaPracticaPreProfesional.objects.get(pk=int(encrypt(request.POST['id'])))
                f = ProgramaPracticaPreProfesionalForm(request.POST)
                if f.is_valid():
                    newfile = None
                    if 'archivoconsejodirectivo' in request.FILES:
                        newfile = request.FILES['archivoconsejodirectivo']
                        newfile._name = generar_nombre("archivoconsejodirectivo_", newfile._name)
                    newfile1 = None
                    if 'archivocomisiongestionacademica' in request.FILES:
                        newfile1 = request.FILES['archivocomisiongestionacademica']
                        newfile1._name = generar_nombre("archivocomisiongestionacademica_", newfile._name)
                    programa.objetivo = f.cleaned_data['objetivo']
                    programa.carrera = f.cleaned_data['carrera']
                    programa.fechadesde = f.cleaned_data['fechadesde']
                    programa.fechahasta = f.cleaned_data['fechahasta']
                    programa.consejodirectivo = f.cleaned_data['consejodirectivo']
                    programa.comisiongestionacademica = f.cleaned_data['comisiongestionacademica']
                    if newfile:
                        programa.archivoconsejodirectivo = newfile
                    if newfile1:
                        programa.archivocomisiongestionacademica = newfile1
                    programa.save(request)
                    log(u'Modificó programa: %s' % programa, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteprograma':
            try:
                programa = ProgramaPracticaPreProfesional.objects.get(pk=int(encrypt(request.POST['id'])))
                # if plan.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"El plan se encuentra en uso, no es posible eliminar."})
                log(u'Eliminó programa: %s' % programa, request, "del")
                programa.status = False
                programa.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcampoitinerario':
            try:
                f = CamposItinerariosMallaForm(request.POST)
                if f.is_valid():
                    campoitinerario = ItinerariosMalla(programa_id=int(request.POST['id']),
                                                       malla=f.cleaned_data['malla'],
                                                       nombre=f.cleaned_data['nombre'],
                                                       nivel=f.cleaned_data['nivel'],
                                                       horas_practicas=f.cleaned_data['horas_practicas'])
                    campoitinerario.save(request)
                    log(u'Adiciono campo itinerario: %s' % campoitinerario, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcampoitinerario':
            try:
                f = CamposItinerariosMallaForm(request.POST)
                campoitinerario = ItinerariosMalla.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    campoitinerario.malla = f.cleaned_data['malla']
                    campoitinerario.nombre = f.cleaned_data['nombre']
                    campoitinerario.nivel = f.cleaned_data['nivel']
                    campoitinerario.horas_practicas = f.cleaned_data['horas_practicas']
                    campoitinerario.save(request)
                    log(u'Modifico campo itinerario: %s' % campoitinerario, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcampoitinerario':
            try:
                campoitinerario = ItinerariosMalla.objects.get(pk=int(encrypt(request.POST['id'])))
                campoitinerario.status = False
                campoitinerario.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'desactivar':
            try:
                programa = ProgramaPracticaPreProfesional.objects.get(id=request.POST['programa'])
                if 'id' in request.POST:
                    itinerario = ItinerariosMalla.objects.get(id=request.POST['id'])
                    itinerario.programa = None
                    itinerario.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'activar':
            try:
                programa = ProgramaPracticaPreProfesional.objects.get(id=request.POST['programa'])
                if 'id' in request.POST:
                    itinerario = ItinerariosMalla.objects.get(id=request.POST['id'])
                    itinerario.programa = programa
                    itinerario.save(request)
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})
        # ACUERDO
        elif action == 'addacuerdo':
            try:
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 10194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = AcuerdoCompromisoForm(request.POST)
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivo", newfile._name)
                    acuerdo = AcuerdoCompromiso(empresa=f.cleaned_data['empresa'],
                                                carrera=f.cleaned_data['carrera'],
                                                fechaelaboracion=f.cleaned_data['fechaelaboracion'],
                                                coordinador=f.cleaned_data['coordinador'],
                                                nombrefirma=f.cleaned_data['nombrefirma'],
                                                cargofirma=f.cleaned_data['cargofirma'],
                                                financiamiento=f.cleaned_data['financiamiento'],
                                                fechainicio=f.cleaned_data['fechainicio'],
                                                fechafinalizacion=f.cleaned_data['fechafinalizacion'],
                                                tiempocump=f.cleaned_data['tiempocump'],
                                                para_practicas=f.cleaned_data['para_practicas'],
                                                para_pasantias=f.cleaned_data['para_pasantias'],
                                                archivo=newfile)
                    acuerdo.save(request)
                    responsables = request.POST.getlist('responsables')
                    if responsables:
                        responsables = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(pk__in=responsables)
                        for rep in responsables:
                            acuerdo.responsables.add(rep)
                    acuerdo.save(request)
                    log(u'Adiciono nuevo acuerdo: %s' % acuerdo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editacuerdo':
            try:
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 10621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                acuerdo = AcuerdoCompromiso.objects.get(pk=int(encrypt(request.POST['id'])))
                f = AcuerdoCompromisoForm(request.POST)
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivo_", newfile._name)
                    if f.cleaned_data['empresa']:
                        acuerdo.empresa = f.cleaned_data['empresa']
                    if f.cleaned_data['carrera']:
                        acuerdo.carrera = f.cleaned_data['carrera']
                    if f.cleaned_data['fechaelaboracion']:
                        acuerdo.fechaelaboracion = f.cleaned_data['fechaelaboracion']
                        #campos nuevos para generar el acuerdo automáticamente
                    if f.cleaned_data['cargofirma']:
                        acuerdo.cargofirma = f.cleaned_data['cargofirma']
                    if f.cleaned_data['nombrefirma']:
                        acuerdo.nombrefirma = f.cleaned_data['nombrefirma']
                    if f.cleaned_data['financiamiento']:
                        acuerdo.financiamiento = f.cleaned_data['financiamiento']
                    if f.cleaned_data['tiempocump']:
                        acuerdo.tiempocump = f.cleaned_data['tiempocump']
                    acuerdo.para_practicas = f.cleaned_data['para_practicas']
                    acuerdo.para_pasantias = f.cleaned_data['para_pasantias']
                    acuerdo.fechafinalizacion = f.cleaned_data['fechafinalizacion']
                    acuerdo.fechainicio = f.cleaned_data['fechainicio']
                    acuerdo.coordinador = f.cleaned_data['coordinador']
                    responsables = request.POST.getlist('responsables')
                    if responsables:
                        acuerdo.responsables.clear()
                        responsables = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(pk__in=responsables)
                        for rep in responsables:
                            acuerdo.responsables.add(rep)
                    if newfile:
                        acuerdo.archivo = newfile
                    acuerdo.save(request)
                    log(u'Modificó acuerdo: %s' % acuerdo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteacuerdo':
            try:
                acuerdo = AcuerdoCompromiso.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó plan: %s' % acuerdo, request, "del")
                acuerdo.status = False
                acuerdo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # EMPRESA
        if action == 'addempresa':
            try:
                if 'logotipo' in request.FILES:
                    d = request.FILES['logotipo']
                    if d.size > 10621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    else:
                        newfiles = request.FILES['logotipo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.png':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                form = EmpleadorPlanPracticaForm(request.POST)
                # form.desbloquear()
                if form.is_valid():
                    newfile = None
                    if 'logotipo' in request.FILES:
                        newfile = request.FILES['logotipo']
                        newfile._name = generar_nombre("logotipo", newfile._name)
                    ruc = form.cleaned_data['ruc']
                    if ruc:
                        if EmpresaEmpleadora.objects.filter(ruc=ruc, status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Empresa ya registrada."})
                    empresa = EmpresaEmpleadora(nombre=form.cleaned_data['nombre'],
                                                ruc=ruc,
                                                provincia_id=request.POST['provincia'],
                                                direccion=form.cleaned_data['direccion'],
                                                telefonos=form.cleaned_data['telefonos'],
                                                autorizada=True,
                                                pais=form.cleaned_data['pais'],
                                                cargo=form.cleaned_data['cargo'],
                                                email=form.cleaned_data['email'],
                                                representante=form.cleaned_data['representante'],
                                                objetivo=form.cleaned_data['objetivo'],
                                                # convenio=form.cleaned_data['convenio'],
                                                tipoinstitucion=int(request.POST['tipoinstitucion']),
                                                sectoreconomico=int(request.POST['sectoreconomico'])
                                                )
                    empresa.save(request)
                    if newfile:
                        empresa.logotipo = newfile
                    log(u'Adicionó empresa: %s' % empresa, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al registrarse."})

        if action == 'editempresa':
            try:
                empresa = EmpresaEmpleadora.objects.get(pk=int(encrypt(request.POST['id'])))
                f = EmpleadorPlanPracticaForm(request.POST)
                if f.is_valid():

                    newfile = None
                    if 'logotipo' in request.FILES:
                        newfile = request.FILES['logotipo']
                        newfile._name = generar_nombre("logotipo", newfile._name)

                    empresa.nombre = f.cleaned_data['nombre']
                    empresa.ruc = f.cleaned_data['ruc']
                    empresa.pais = f.cleaned_data['pais']
                    empresa.provincia = f.cleaned_data['provincia']
                    empresa.direccion = f.cleaned_data['direccion']
                    empresa.telefonos = f.cleaned_data['telefonos']
                    empresa.cargo = f.cleaned_data['cargo']
                    empresa.email = f.cleaned_data['email']
                    empresa.representante = f.cleaned_data['representante']
                    empresa.objetivo = f.cleaned_data['objetivo']
                    empresa.tipoinstitucion = f.cleaned_data['tipoinstitucion']
                    empresa.sectoreconomico = f.cleaned_data['sectoreconomico']
                    if newfile:
                        empresa.logotipo = newfile
                    empresa.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delempresa':
            try:
                with transaction.atomic():
                    instancia = EmpresaEmpleadora.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Empresa Empleadora: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addactividad':
            try:

                f = ActividadItinerarioForm(request.POST)
                if f.is_valid():
                    itinerario = ItinerariosMalla.objects.get(pk=request.POST['iditinerario'])

                    actividad = ActividadItinerario(itinerarios_malla_id=itinerario.id,
                                                    descripcion=f.cleaned_data['descripcion'])
                    actividad.save(request)
                    log(u'Adiciono actividad itinerario: %s' % actividad.descripcion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editactividad':
            try:

                f = ActividadItinerarioForm(request.POST)
                if f.is_valid():
                    actividad = ActividadItinerario.objects.get(pk=request.POST['idactividad'])
                    actividad.descripcion = f.cleaned_data['descripcion']
                    actividad.save(request)
                    log(u'Edicion actividad itinerario: %s' % actividad.descripcion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteactividad':
            try:
                actividad = ActividadItinerario.objects.get(pk=request.POST['id'])
                log(u'Eliminó actividad: %s' % actividad.descripcion, request, "del")
                actividad.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcoordinador':
            try:
                postar = AcuerdoCompromiso.objects.get(id=int(request.POST['id']))
                form = CoordinadorAcuerdoForm(request.POST)
                if form.is_valid():
                    postar.coordinador = form.cleaned_data['coordinador']
                    postar.save(request)
                    log(u'Adiciono Coordinador Unemi Acuerdos de Compromiso : %s' % (postar), request, "add")
                    return JsonResponse({"result": False,}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        elif action == 'addresponsables':
            try:
                postar = AcuerdoCompromiso.objects.get(id=int(request.POST['id']))
                form = ResponsablesAcuerdoForm(request.POST)
                if form.is_valid():
                    postar.responsables.clear()
                    for r in form.cleaned_data['responsables']:
                        postar.responsables.add(r)
                    #postar.responsables = form.cleaned_data['responsables']
                    postar.save(request)
                    log(u'Adiciono Responsables en Acuerdos de Compromiso : %s' % (postar), request, "add")
                    return JsonResponse({"result": False,}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        elif action == 'adddocumento':
            try:
                with transaction.atomic():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 10194304:
                            return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        # if exte in ['pdf','jpg','jpeg','png','jpeg','peg','PDF']:
                        if exte:
                            newfile._name = generar_nombre("acuerdo_compromiso_", newfile._name)
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})
                    else:
                        return JsonResponse({"result": True, "mensaje": u"Debe adicionar un documento"})
                    filtro = AcuerdoCompromiso.objects.get(pk=request.POST['id'])
                    if 'archivo' in request.FILES:
                        filtro.archivo = newfile
                        filtro.subeacuerdo = persona
                        filtro.fechasube = hoy
                    filtro.save(request)
                    log(u'Adiciono Acuerdo de Compromiso: %s' % filtro, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'anularacuerdo':
            id = request.POST['id']
            acuerdo = AcuerdoCompromiso.objects.get(id=id)
            mensaje = 'Marco como '
            if acuerdo.anulado:
                acuerdo.anulado = False
                acuerdo.observacionanulado = ''
                mensaje = 'Quito anulacion de acuerdo %s' % acuerdo
            else:
                observacion = request.POST['observacion'] if 'observacion' in request.POST else ''
                acuerdo.anulado = True
                if observacion and not observacion == '':
                    acuerdo.observacionanulado = observacion
                mensaje += 'como acuerdo anulado %s' % acuerdo
            acuerdo.save(request)
            log(str(mensaje), request, 'edit')
            return JsonResponse({"result": "ok"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Plan'
                    data['form'] = PlanPracticaPreProfesionalForm()
                    return render(request, "adm_planpractica/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar plan'
                    data['plan'] = plan = PlanPracticaPreProfesional.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(plan)
                    form = PlanPracticaPreProfesionalForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_planpractica/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Borrar plan'
                    data['plan'] = PlanPracticaPreProfesional.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_planpractica/delete.html", data)
                except Exception as ex:
                    pass

            elif action == 'programas':
                try:
                    data['title'] = u'Gestión de programas de prácticas preprofesionales'
                    search = None
                    ids = None
                    data['plan'] = plan = PlanPracticaPreProfesional.objects.get(pk=int(encrypt(request.GET['idp'])))
                    programas = ProgramaPracticaPreProfesional.objects.filter(status=True, plan=plan)
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        programas = programas.filter(Q(objetivo__icontains=search))
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        programas = programas.filter(id=ids)
                    paging = MiPaginador(programas, 20)
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
                    data['programas'] = page.object_list
                    data['reporte_0'] = obtener_reporte("programapracticas")
                    return render(request, "adm_planpractica/programas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addprograma':
                try:
                    data['title'] = u'Adicionar Programa'
                    data['form'] = ProgramaPracticaPreProfesionalForm()
                    data['plan'] = PlanPracticaPreProfesional.objects.get(pk=int(encrypt(request.GET['idp'])))
                    return render(request, "adm_planpractica/addprograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'editprograma':
                try:
                    data['title'] = u'Editar programa'
                    data['programa'] = programa = ProgramaPracticaPreProfesional.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(programa)
                    form = ProgramaPracticaPreProfesionalForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_planpractica/editprograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteprograma':
                try:
                    data['title'] = u'Borrar programa'
                    data['programa'] = ProgramaPracticaPreProfesional.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_planpractica/deleteprograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'itinerarios':
                try:
                    data['title'] = u'Gestión de itinerarios'
                    search = None
                    ids = None
                    data['programa'] = programa = ProgramaPracticaPreProfesional.objects.get(pk=request.GET['idp'])
                    itinerarios1 = ItinerariosMalla.objects.filter(status=True, programa=programa).order_by('nombre')
                    itinerarios2 = ItinerariosMalla.objects.filter(status=True,malla__carrera=programa.carrera).order_by('nombre')
                    itinerarios = itinerarios1 | itinerarios2
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        itinerarios = itinerarios.filter(Q(nombre__icontains=search))
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        itinerarios = itinerarios.filter(id=ids)
                    paging = MiPaginador(itinerarios, 20)
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
                    data['itinerarios'] = page.object_list
                    return render(request, "adm_planpractica/itinerarios.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcampoitinerario':
                try:
                    data['title'] = u'Adicionar itinerario'
                    data['programa'] = programa = ProgramaPracticaPreProfesional.objects.get(pk=int(request.GET['idp']))
                    form = CamposItinerariosMallaForm()
                    form.ponercarrera(programa.carrera)
                    data['form'] = form
                    return render(request, "adm_planpractica/addcampoitinerario.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcampoitinerario':
                try:
                    data['title'] = u'Editar itinerario'
                    data['campoitinerario'] = campoitinerario = ItinerariosMalla.objects.get(
                        pk=int(request.GET['idcampoitinerario']))
                    data['programa'] = programa = ProgramaPracticaPreProfesional.objects.get(pk=int(request.GET['idp']))
                    form = CamposItinerariosMallaForm(initial={'nombre': campoitinerario.nombre,
                                                               'nivel': campoitinerario.nivel,
                                                               'horas_practicas': campoitinerario.horas_practicas,
                                                               'malla': campoitinerario.malla,
                                                               })
                    form.ponercarrera(programa.carrera)
                    data['form'] = form
                    return render(request, "adm_planpractica/editcampoitinerario.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcampoitinerario':
                try:
                    data['title'] = u'Eliminar itinerario'
                    data['campoitinerario'] = ItinerariosMalla.objects.get(pk=int(request.GET['idcampoitinerario']))
                    return render(request, "adm_planpractica/delcampoitinerario.html", data)
                except Exception as ex:
                    pass

            elif action == 'carrerasplan':
                try:
                    data = {}
                    data['plan'] = plan = PlanPracticaPreProfesional.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['carreras'] = plan.programapracticapreprofesional_set.values_list('carrera__nombre',
                                                                                           flat=True).filter(
                        status=True).distinct()
                    template = get_template("adm_planpractica/carrerasplan.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # ACUERDOS COMPROMISO
            elif action == 'acuerdoscompromisos':
                try:
                    data['title'] = u'Gestión de acuerdo de compromisos'
                    querybase = AcuerdoCompromiso.objects.filter(status=True).order_by('-pk')
                    tipo,carrera,total, desde, hasta, search, filtros, url_vars = request.GET.get('tipo', ''),request.GET.get('carrera', ''), request.GET.get('total', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('search', ''), Q(status=True), ''
                    if desde:
                        data['desde'] = desde
                        url_vars += "&desde={}".format(desde)
                        filtros = filtros & Q(fechafinalizacion__gte=desde)
                    if hasta:
                        data['hasta'] = hasta
                        url_vars += "&hasta={}".format(hasta)
                        filtros = filtros & Q(fechafinalizacion__lte=hasta)
                    if tipo:
                        data['tipo'] = tipo
                        url_vars += "&tipo={}".format(tipo)
                        if tipo == '1':
                            filtros = filtros & ~Q(archivo='')
                        if tipo == '2':
                            filtros = filtros & Q(archivo='')
                        if tipo == '3':
                            filtros = filtros & Q(para_practicas=True)
                        if tipo == '4':
                            filtros = filtros & Q(para_pasantias=True)
                        if tipo == '5':
                            filtros = filtros & (Q(para_practicas=True) & Q(para_pasantias=True))
                        if tipo == '6':
                            filtros = filtros & (Q(anulado=True))
                        if tipo == '7':
                            filtros = filtros & (Q(anulado=False))
                    if carrera:
                        data['carreraid'] = int(carrera)
                        url_vars += "&carrera={}".format(carrera)
                        filtros = filtros & Q(carrera_id=carrera)
                    if total:
                        data['total'] = total
                        url_vars += "&total={}".format(total)
                        if total == '1':
                            acuerdo = AcuerdoCompromiso.objects.annotate(total=Count('practicaspreprofesionalesinscripcion',filter=Q(practicaspreprofesionalesinscripcion__status=True) & ~Q(practicaspreprofesionalesinscripcion__estadosolicitud=3))).filter(total=0)
                            filtros = filtros & Q(pk__in=acuerdo.values_list('pk', flat=True))
                        elif total == '2':
                            acuerdo = AcuerdoCompromiso.objects.annotate(total=Count('practicaspreprofesionalesinscripcion',filter=Q(practicaspreprofesionalesinscripcion__status=True) & ~Q(practicaspreprofesionalesinscripcion__estadosolicitud=3))).filter(total__gt=0)
                            filtros = filtros & Q(pk__in=acuerdo.values_list('pk', flat=True))
                    if search:
                        data['search'] = search
                        s = search.split()
                        filtros = filtros & (Q(empresa__nombre__icontains=search) | Q(carrera__nombre__icontains=search))
                        url_vars += '&search={}'.format(search)
                    url_vars += '&action={}'.format(action)
                    data["url_vars"] = url_vars
                    query = querybase.filter(filtros).order_by('-pk')
                    data['listcount'] = query.count()

                    if 'export_to_excel' in request.GET:
                        try:
                            __author__ = 'Unemi'
                            title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                            font_style = XFStyle()
                            font_style.font.bold = True
                            font_style2 = XFStyle()
                            font_style2.font.bold = False
                            wb = Workbook(encoding='utf-8')
                            ws = wb.add_sheet('practicas')
                            ws.write_merge(0, 0, 0, 5, 'REPORTE DE ACUERDOS DE COMPROMISO', title)
                            response = HttpResponse(content_type="application/ms-excel")
                            response['Content-Disposition'] = 'attachment; filename=listado_acuerdos_filtrado_' + random.randint(1, 10000).__str__() + '.xls'
                            columns = [
                                (u"N°", 1000),
                                (u"CARRERA", 5000),
                                (u"MODALIDAD", 4000),
                                (u"COORDINADOR UNEMI", 10000),
                                (u"CARGO UNEMI", 7000),
                                (u"EMPRESA", 13000),
                                (u"RUC", 5000),
                                (u"FIRMA EMPRESA", 10000),
                                (u"CARGO EN EMPRESA", 7000),
                                (u"CORREO EMPRESA", 7000),
                                (u"TELF. EMPRESA", 5000),
                                (u"DIRECCION EMPRESA", 10000),
                                (u"TIEMPO CUMPLIMIENTO", 5000),
                                (u"TIPO INSTITUCIÓN", 5000),
                                (u"SECTOR ECONOMICO", 5000),
                                (u"APLICA PRACTICAS", 5000),
                                (u"APLICA PASANTIAS", 5000),
                                (u"# VINCULADOS", 5000),
                                (u"FECHA ELABORACIÓN", 5000),
                                (u"FECHA INICIO", 5000),
                                (u"FECHA FIN", 5000),
                                (u"ARCHIVO", 4000),
                                (u"ENLACE ACUERDO", 15000),
                                (u"ANULADO", 3000),
                                (u"GENERO ACUERDO", 4000),
                                (u"FECHA ACUERDO", 4000),

                            ]
                            row_num = 1
                            for col_num in range(len(columns)):
                                ws.write(row_num, col_num, columns[col_num][0], font_style)
                                ws.col(col_num).width = columns[col_num][1]
                            date_format = xlwt.XFStyle()
                            date_format.num_format_str = 'yyyy/mm/dd'
                            media = 'https://sga.unemi.edu.ec/media/'
                            row_num = 2

                            for index, acuerdo in enumerate(query):
                                inicio = acuerdo.fechainicio
                                fin = acuerdo.fechafinalizacion
                                fechacumplimiento = calcular_tiempo_cumplimiento(inicio, fin)
                                ws.write(row_num, 0, index + 1, font_style2)
                                ws.write(row_num, 1, acuerdo.carrera.nombre_completo(), font_style2)
                                ws.write(row_num, 2, acuerdo.carrera.get_modalidad_display(), font_style2)
                                ws.write(row_num, 3,acuerdo.coordinador.nombres.upper() if acuerdo.coordinador else "", font_style2)
                                ws.write(row_num, 4,acuerdo.coordinador.cargo.upper() if acuerdo.coordinador else "", font_style2)
                                ws.write(row_num, 5, acuerdo.empresa.nombre.upper(), font_style2)
                                ws.write(row_num, 6, acuerdo.empresa.ruc, font_style2)
                                ws.write(row_num, 7, acuerdo.nombrefirma.upper() if acuerdo.nombrefirma else "", font_style2)
                                ws.write(row_num, 8, acuerdo.cargofirma.upper() if acuerdo.cargofirma else "", font_style2)
                                ws.write(row_num, 9, acuerdo.empresa.email, date_format)
                                ws.write(row_num, 10, acuerdo.empresa.telefonos, date_format)
                                ws.write(row_num, 11, acuerdo.empresa.direccion, font_style2)
                                ws.write(row_num, 12, fechacumplimiento, font_style2)
                                ws.write(row_num, 13, acuerdo.empresa.get_tipoinstitucion_display(), date_format)
                                ws.write(row_num, 14, acuerdo.empresa.get_sectoreconomico_display(), date_format)
                                ws.write(row_num, 15, "SI" if acuerdo.para_practicas else "NO", font_style2)
                                ws.write(row_num, 16, "SI" if acuerdo.para_pasantias else "NO", font_style2)
                                ws.write(row_num, 17, acuerdo.totalvinculados(), font_style2)
                                ws.write(row_num, 18, acuerdo.fechaelaboracion, date_format)
                                ws.write(row_num, 19, inicio, date_format)
                                ws.write(row_num, 20, fin, date_format)
                                ws.write(row_num, 21, "SI" if acuerdo.archivo else "NO", font_style2)
                                ws.write(row_num, 22, media + str(acuerdo.archivo) if acuerdo.archivo else "NO EXISTE",font_style2)
                                ws.write(row_num, 23, "SI" if acuerdo.anulado else "NO", font_style2)
                                ws.write(row_num, 24, str(acuerdo.usuario_creacion) if acuerdo.usuario_creacion else "",font_style2)
                                ws.write(row_num, 25, acuerdo.fecha_creacion, date_format)
                                row_num += 1
                            wb.save(response)
                            return response
                        except Exception as ex:
                            pass
                    paging = MiPaginador(query, 20)
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
                    data['acuerdos'] = page.object_list
                    data['con_documentos'] = query.exclude(archivo='').count()
                    data['sin_documentos'] = query.filter(archivo='').count()
                    data['listcarreras'] = Carrera.objects.filter(status=True,coordinacion__in=(1,2,3,4,5)).order_by('nombre')
                    querybasepracticas = PracticasPreprofesionalesInscripcion.objects.select_related('acuerdo').filter(status=True, acuerdo__in=query.values_list('pk', flat=True)).exclude(estadosolicitud=3)
                    filtrospracticas = Q(status=True)
                    if desde:
                        filtrospracticas = filtrospracticas & Q(fecha_creacion__gte=desde)
                    if hasta:
                        filtrospracticas = filtrospracticas & Q(fecha_creacion__lte=hasta)
                    data['topempresas'] = querybasepracticas.filter(filtrospracticas).values_list('acuerdo__empresa',flat=True).annotate(totcount=Count('acuerdo__empresa')).values('acuerdo__empresa__nombre', 'totcount').order_by('-totcount')[:15]
                    return render(request, "adm_planpractica/acuerdoscompromisos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addacuerdo':
                try:
                    data['title'] = u'Adicionar Acuerdo'
                    data['form'] = AcuerdoCompromisoForm()
                    return render(request, "adm_planpractica/addacuerdo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editacuerdo':
                try:
                    data['title'] = u'Editar acuerdo'
                    data['acuerdo'] = acuerdo = AcuerdoCompromiso.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(acuerdo)
                    form = AcuerdoCompromisoForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_planpractica/editacuerdo.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteacuerdo':
                try:
                    data['title'] = u'Borrar acuerdo'
                    data['acuerdo'] = AcuerdoCompromiso.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_planpractica/deleteacuerdo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addresponsables':
                try:
                    data['filtro'] = filtro = AcuerdoCompromiso.objects.get(pk=int(request.GET['id']))
                    form = ResponsablesAcuerdoForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_planpractica/modal/modalform.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addcoordinador':
                try:
                    data['filtro'] = filtro = AcuerdoCompromiso.objects.get(pk=int(request.GET['id']))
                    form = CoordinadorAcuerdoForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_planpractica/modal/modalform.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'vervinculados':
                try:
                    data['filtro'] = filtro = AcuerdoCompromiso.objects.get(pk=int(request.GET['id']))
                    data['listado'] = listado = PracticasPreprofesionalesInscripcion.objects.filter(status=True, acuerdo=filtro).exclude(estadosolicitud=3).order_by('-pk')
                    template = get_template("adm_planpractica/modal/vervinculados.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adddocumento':
                try:
                    data['filtro'] = filtro = AcuerdoCompromiso.objects.get(pk=int(request.GET['id']))
                    form = ArchivoAcuerdoForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_planpractica/modal/modalform.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'empresa':
                try:
                    data['title'] = u'Gestión de empresas'
                    search = None
                    ids = None
                    if 'se' in request.GET:
                        search = request.GET['se']
                        empresa = EmpresaEmpleadora.objects.filter(
                            Q(nombre__icontains=search) | Q(ruc__icontains=search))
                    elif 'ide' in request.GET:
                        ids = int(encrypt(request.GET['ide']))
                        empresa = EmpresaEmpleadora.objects.filter(id=ids)
                    else:
                        empresa = EmpresaEmpleadora.objects.filter(status=True).order_by('-convenio', 'nombre')
                    paging = MiPaginador(empresa.filter(status=True), 25)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['empresas'] = page.object_list
                    data['clave'] = DEFAULT_PASSWORD
                    return render(request, "adm_planpractica/viewempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'addempresa':
                try:
                    data['title'] = u"Adicionar empresa"
                    form = EmpleadorPlanPracticaForm()
                    form.adicionar()
                    # form.bloquear()
                    data['form'] = form
                    return render(request, "adm_planpractica/addempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'editempresa':
                try:
                    data['title'] = u"Editar datos del Empleador"
                    empresa = EmpresaEmpleadora.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['empresa'] = empresa
                    form = EmpleadorPlanPracticaForm(initial=model_to_dict(empresa))
                    form.editar(empresa.pais)
                    # if empresa.convenio==False:
                    #     form.bloquear()
                    data['form'] = form
                    return render(request, "adm_planpractica/editempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'delempresa':
                try:
                    data['title'] = u'Eliminar empresa empleadora'
                    data['empresa'] = EmpresaEmpleadora.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_planpractica/delempresa.html", data)
                except Exception as ex:
                    pass

            elif action == 'autorizar':
                try:
                    empresa = EmpresaEmpleadora.objects.get(pk=request.GET['id'])
                    empresa.autorizada = True
                    empresa.save(request)
                    log(u'Autorizo empresa empleadora: %s' % empresa, request, "edit")
                    empleador = empresa.empleador_set.all()[0]
                    send_html_mail("Registro a bolsa laboral autorizado", "emails/autorizacionnuevoregistro.html",
                                   {'sistema': request.session['nombresistema'], 'e': empleador, 't': miinstitucion(),
                                    'modelo': MODELO_EVALUACION, 'dominio': EMAIL_DOMAIN},
                                   empleador.persona.lista_emails_envio(), [])
                    return HttpResponseRedirect("/adm_planpractica?action=empresa&id" + request.GET['id'])
                except Exception as ex:
                    return HttpResponseRedirect("/adm_planpractica?action=empresa")

            elif action == 'desautorizar':
                try:
                    empresa = EmpresaEmpleadora.objects.get(pk=request.GET['id'])
                    empresa.autorizada = False
                    empresa.save()
                    log(u'Desautoriza empresa empleadora: %s' % empresa, request, "edit")
                    return HttpResponseRedirect("/adm_planpractica?action=empresa&id" + request.GET['id'])
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponseRedirect("/adm_planpractica?action=empresa")

            elif action == 'resetear':
                try:
                    data['title'] = u'Resetear clave'
                    empleador = Persona.objects.get(pk=int(request.GET['id']))
                    data['empleador'] = empleador
                    return render(request, "adm_planpractica/resetear.html", data)
                except Exception as ex:
                    pass

            #                              cambiando actividades
            elif action == 'actividades':
                try:
                    data['title'] = u'Actividades'
                    data['itinerario'] = itinerario =  ItinerariosMalla.objects.get(pk=request.GET['iditinerario'])
                    data['actividades'] = itinerario.actividaditinerario_set.filter(status=True).order_by('id')
                    data['idp'] = request.GET['idp']
                    return render(request, "adm_planpractica/actividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'addactividad':
                try:
                    data['title'] = u'Adicionar Actividad'
                    data['itinerario'] = ItinerariosMalla.objects.get(pk=request.GET['iditinerario'])
                    data['idp'] = request.GET['idp']
                    data['form'] = ActividadItinerarioForm()
                    return render(request, "adm_planpractica/addactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['title'] = u'Editar Actividad'
                    data['actividad'] = actividad = ActividadItinerario.objects.get(pk=request.GET['idactividad'])
                    data['idp'] = request.GET['idp']
                    data['form'] = ActividadItinerarioForm(initial=model_to_dict(actividad))
                    return render(request, "adm_planpractica/editactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteactividad':
                try:
                    data['title'] = u'Borrar Actividad'
                    data['actividad'] = ActividadItinerario.objects.get(pk=request.GET['id'])
                    return render(request, "adm_planpractica/deleteactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'informereporteacuerdocompromiso':
                try:
                    data['title'] = u'Carta de Vinculacion'
                    data['acuerdo'] = acuerdo = AcuerdoCompromiso.objects.get(pk=int(request.GET['id']))
                    data['fechaimpresion'] = fecha = acuerdo.fechaelaboracion
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    if responsablevinculacion:
                        data['responsablevinculacion'] = responsablevinculacion
                        # firma = FirmaPersona.objects.filter(persona=responsablevinculacion, tipofirma=2, status=True).first()
                        # data['firmaimg'] = firma if firma else None
                    data['fechalatras'] = fechaletra_corta(acuerdo.fechaelaboracion)
                    nombreempresa = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((acuerdo.empresa.nombre).replace(' ','_')))
                    nombrearchivo = 'ACUERDO_COMPROMISO_{}_{}'.format(nombreempresa,random.randint(1, 100000).__str__())
                    # data['carta'] = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    # data['firma'] = ConfiguracionFirmaPracticasPreprofesionales.objects.get(pk=int(encrypt(request.GET['id'])))
                    # return render(request, "", data)
                    # if acuerdo:
                    #     acuerdo.generaacuerdo = persona
                    #     acuerdo.fechagenera = hoy
                    #     acuerdo.save()
                    return conviert_html_to_pdf_name(
                        'adm_planpractica/informereporteacuerdocompromiso.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }, nombrearchivo
                    )
                    # return conviert_html_to_pdf(
                    #     'adm_planpractica/informereporteacuerdocompromiso.html',
                    #     {
                    #         'pagesize': 'A4',
                    #         'data': data,
                    #     },
                    # )
                except Exception as ex:
                    pass

            elif action == 'excelacuerdogeneral':
                try:
                    __author__ = 'Unemi'
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 5, 'REPORTE DE ACUERDOS DE COMPROMISO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_acuerdos_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"N°", 1000),
                        (u"CARRERA", 5000),
                        (u"MODALIDAD", 4000),
                        (u"COORDINADOR UNEMI", 10000),
                        (u"CARGO UNEMI", 7000),
                        (u"EMPRESA", 13000),
                        (u"RUC", 5000),
                        (u"FIRMA EMPRESA", 10000),
                        (u"CARGO EN EMPRESA", 7000),
                        (u"CORREO EMPRESA", 7000),
                        (u"TELF. EMPRESA", 5000),
                        (u"DIRECCION EMPRESA", 10000),
                        (u"TIEMPO CUMPLIMIENTO", 5000),
                        (u"TIPO INSTITUCIÓN", 5000),
                        (u"SECTOR ECONOMICO", 5000),
                        (u"APLICA PRACTICAS", 5000),
                        (u"APLICA PASANTIAS", 5000),
                        (u"# VINCULADOS", 5000),
                        (u"FECHA ELABORACIÓN", 5000),
                        (u"FECHA INICIO", 5000),
                        (u"FECHA FIN", 5000),
                        (u"ARCHIVO", 4000),
                        (u"ENLACE ACUERDO", 15000),
                        (u"ANULADO", 3000),
                        (u"GENERO ACUERDO", 4000),
                        (u"FECHA ACUERDO", 4000),

                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    media = 'https://sga.unemi.edu.ec/media/'
                    listaacuerdo = AcuerdoCompromiso.objects.filter(status=True).order_by('empresa__nombre')
                    row_num = 2
                    for index, acuerdo in enumerate(listaacuerdo):
                        inicio = acuerdo.fechainicio
                        fin = acuerdo.fechafinalizacion
                        fechacumplimiento = calcular_tiempo_cumplimiento(inicio,fin)
                        ws.write(row_num, 0, index + 1, font_style2)
                        ws.write(row_num, 1, acuerdo.carrera.nombre_completo(), font_style2)
                        ws.write(row_num, 2, acuerdo.carrera.get_modalidad_display(), font_style2)
                        ws.write(row_num, 3, acuerdo.coordinador.nombres.upper() if acuerdo.coordinador else "", font_style2)
                        ws.write(row_num, 4, acuerdo.coordinador.cargo.upper() if acuerdo.coordinador else "", font_style2)
                        ws.write(row_num, 5, acuerdo.empresa.nombre.upper(), font_style2)
                        ws.write(row_num, 6, acuerdo.empresa.ruc, font_style2)
                        ws.write(row_num, 7, acuerdo.nombrefirma.upper() if acuerdo.nombrefirma else "", font_style2)
                        ws.write(row_num, 8, acuerdo.cargofirma.upper() if acuerdo.cargofirma else "", font_style2)
                        ws.write(row_num, 9, acuerdo.empresa.email, date_format)
                        ws.write(row_num, 10, acuerdo.empresa.telefonos, date_format)
                        ws.write(row_num, 11, acuerdo.empresa.direccion, font_style2)
                        ws.write(row_num, 12, fechacumplimiento, font_style2)
                        ws.write(row_num, 13, acuerdo.empresa.get_tipoinstitucion_display(), date_format)
                        ws.write(row_num, 14, acuerdo.empresa.get_sectoreconomico_display(), date_format)
                        ws.write(row_num, 15, "SI" if acuerdo.para_practicas else "NO", font_style2)
                        ws.write(row_num, 16, "SI" if acuerdo.para_pasantias else "NO", font_style2)
                        ws.write(row_num, 17, acuerdo.totalvinculados(), font_style2)
                        ws.write(row_num, 18, acuerdo.fechaelaboracion, date_format)
                        ws.write(row_num, 19, inicio, date_format)
                        ws.write(row_num, 20, fin, date_format)
                        ws.write(row_num, 21, "SI" if acuerdo.archivo else "NO", font_style2)
                        ws.write(row_num, 22, media + str(acuerdo.archivo) if acuerdo.archivo else "NO EXISTE",font_style2)
                        ws.write(row_num, 23, "SI" if acuerdo.anulado else "NO", font_style2)
                        ws.write(row_num, 24, str(acuerdo.usuario_creacion) if acuerdo.usuario_creacion else "",font_style2)
                        ws.write(row_num, 25, acuerdo.fecha_creacion, date_format)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Gestión de de plan de prácticas preprofesionales'
                search = None
                ids = None
                plan = PlanPracticaPreProfesional.objects.filter(status=True)
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    plan = plan.filter(Q(objetivo__icontains=search))
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    plan = plan.filter(id=ids)
                paging = MiPaginador(plan, 20)
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
                data['planes'] = page.object_list
                data['reporte_0'] = obtener_reporte('planpracticas')
                return render(request, "adm_planpractica/view.html", data)
            except Exception as ex:
                pass