import json
import sys
import calendar
from _decimal import Decimal
from datetime import datetime, timedelta, date
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from decorators import secure_module, last_access
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.forms import model_to_dict
from sga.commonviews import adduserdata, obtener_reporte, materias_abiertas, matricular
from sga.templatetags.sga_extras import encrypt, encrypt_alu, nombremes
from settings import DEBUG, HOMITIRCAPACIDADHORARIO, UTILIZA_GRATUIDADES, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, PORCIENTO_PERDIDA_TOTAL_GRATUIDAD, NOTA_ESTADO_EN_CURSO, CALCULO_POR_CREDITO
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_name
from sga.funciones import MiPaginador, generar_nombre, log, notificacion, variable_valor, elimina_tildes, to_unicode
from inno.funciones import haber_aprobado_modulos_ingles, haber_aprobado_modulos_computacion, matricularSalud, inscripcion_practicas_salud, materias_abiertas_salud, matricularSaludCero
from inno.forms import BitacoraActividadPppForm, DiscapacidadSaludForm, PersonaEnfermedadSaludForm, PersonaDetalleMaternidadSaludForm, FamiliarSaludForm, \
    FamiliarNinioSaludForm, FamiliarEnfermedadSaludForm, RequisitoPPPSaludForm
from django.contrib import messages
from django.db.models import Q, Max, Count, PROTECT, Sum, Avg, Min, F, ExpressionWrapper, DurationField, TimeField, DateTimeField
from dateutil.rrule import MONTHLY, rrule
from inno.models import ConfiguracionInscripcionPracticasPP, HistorialInscricionOferta, BitacoraActividadEstudiantePpp, DetalleBitacoraEstudiantePpp,\
    PracticasPreprofesionalesInscripcionExtensionSalud, PerfilInscripcionExtensionSalud, PersonaEnfermedadExtensionSalud, PersonaDetalleMaternidadExtensionSalud, \
    ExtPreInscripcionPracticasPP, PersonaDatosFamiliares, PersonaDatosFamiliaresExtensionSalud, EnfermedadFamiliarSalud, HistorialDocumentosPPPSalud, \
    OrdenPrioridadInscripcion, ItinerarioAsignaturaSalud, RequisitoPracticappSalud
from sga.models import Inscripcion, PreInscripcionPracticasPP, DetallePreInscripcionPracticasPP, ConfigMatriculacionPrimerNivel, \
    DetalleRecoridoPreInscripcionPracticasPP, Profesor, CUENTAS_CORREOS, PracticasPreprofesionalesInscripcion, Persona, PersonaEnfermedad, PersonaDetalleMaternidad, \
    PerfilUsuario, Externo, Nivel, Periodo, Asignatura, AsignaturaMalla, Materia, MateriaAsignada, AlumnosPracticaMateria, AgregacionEliminacionMaterias, miinstitucion,\
    GruposProfesorMateria, ProfesorMateria
from matricula.models import PeriodoMatricula, Matricula
from matricula.funciones import get_nivel_matriculacion, get_tipo_matricula, TIPO_PROFESOR_PRACTICA, calcula_nivel
from sga.tasks import send_html_mail

unicode = str

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    periodo = request.session['periodo']
    data['coordinacion'] = coordinacion = request.session['coordinacion']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    if not periodo:
        return HttpResponseRedirect("/?info=Estimado docente, no tiene asignaturas en distributivo.")
    inscripcion = perfilprincipal.inscripcion
    hoy = datetime.now().date()
    hoytime = datetime.now()
    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://localhost:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
    persona_valida = Persona.objects.get(pk=26212)
    periodo_matricular = Periodo.objects.get(pk=variable_valor('PERIODO_MATRICULA_PRACTICAS_SALUD_ID'))
    data['habilita_matricula_salud'] = habilita_matricula_salud = variable_valor('HABILITA_MATRICULA_PRACTICAS_SALUD')
    data['habilita_inscripcion_nivel'] = habilita_inscripcion_nivel = variable_valor('HABILITA_INSCRIPCION_NIVEL_SALUD')
    data['eMatricula'] = eMatricula = inscripcion.matricula_periodo(periodo_matricular)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'inscribirpracticapp':
            try:
                turno = int(request.POST.get('idturno', '0'))
                configuracionoferta = ConfiguracionInscripcionPracticasPP.objects.get(status=True, pk=int(request.POST['idconfig']))
                preins = DetallePreInscripcionPracticasPP.objects.get(pk=int(request.POST['idpreins']))
                practicas, msg = inscripcion_practicas_salud(request, preins, configuracionoferta, turno)
                if habilita_inscripcion_nivel: #permite inscribir en todos los itinirarios del nivel
                    fecha_practica = [configuracionoferta.fechainicio]
                    itinerarios = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True, nivel=preins.itinerariomalla.nivel).exclude(pk=preins.itinerariomalla.id)
                    if practicas:
                        for i in itinerarios:
                            if configuracion2 := ConfiguracionInscripcionPracticasPP.objects.filter(status=True, itinerariomalla__in=[i], estado=2, asignacionempresapractica=configuracionoferta.asignacionempresapractica, dia=configuracionoferta.dia).exclude(fechainicio__in=fecha_practica):
                                lista_ordenado_cupos = sorted(configuracion2, key=lambda x: x.cupos_disponibles(), reverse=True)
                                config = lista_ordenado_cupos[0]
                                if config.cupos_disponibles() > 0:
                                    if preins2 := DetallePreInscripcionPracticasPP.objects.filter(status=True, preinscripcion=preins.preinscripcion, inscripcion=preins.inscripcion, itinerariomalla=i).first():
                                        practicas, msg = inscripcion_practicas_salud(request, preins2, config, turno)
                                        if practicas: fecha_practica.append(config.fechainicio)
                    else:
                        raise NameError(msg)
                if practicas:
                    if habilita_matricula_salud:
                        if not eMatricula:
                            return matricularSaludCero(request, True, True) #Matricula por primera vez
                        else:
                            return matricularSalud(request, eMatricula, True) #Ya cuenta con una matrícula
                    else:#Solo se inscribe en las prácticas
                        return JsonResponse({"result": "ok"})
                else:
                    raise NameError(msg)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"{str(ex)}. Error al guardar los datos."})

        elif action == 'addresultados':
            with transaction.atomic():
                try:
                    bitacora = BitacoraActividadEstudiantePpp.objects.get(pk=int(request.POST['id']))
                    if bitacora:
                        bitacora.resultado = request.POST['val']
                        bitacora.save(request)
                        log(u'Modificó producto/resultado de bitácora: %s' % bitacora, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

        elif action == 'addplanaccion':
            with transaction.atomic():
                try:
                    bitacora = BitacoraActividadEstudiantePpp.objects.get(pk=int(request.POST['id']))
                    if bitacora:
                        bitacora.planaccion = request.POST['val']
                        bitacora.save(request)
                        log(u'Modificó plan de acción de bitácora: %s' % bitacora, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

        elif action == 'addbitacorappp':
            try:
                with transaction.atomic():
                    form = BitacoraActividadPppForm(request.POST)

                    hi = request.POST['hora'] if 'hora' in request.POST else ''
                    hf = request.POST['horafin'] if 'horafin' in request.POST else ''
                    if not hi:
                        return JsonResponse({"result": "bad", "mensaje": "Seleccione la hora de inicio de la actividad."})
                    if hi and hf:
                        h1 = timedelta(hours=int(hi.split(':')[0]), minutes=int(hi.split(':')[1]))
                        h2 = timedelta(hours=int(hf.split(':')[0]), minutes=int(hf.split(':')[1]))
                        if h2 <= h1:
                            return JsonResponse({"result": "bad", "mensaje": "Hora fin no puede ser menor o igual que hora inicio."})
                        total = f"{h2 - h1}"
                        if int(total.split(':')[0]) == 0 and int(total.split(':')[1]) < 59:
                            return JsonResponse({"result": "bad", "mensaje": "La duración de la actividad debe ser mayor a 59 minutos."})

                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if newfile.size > 12582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            if newfile:
                                newfile._name = generar_nombre("bitacora", newfile._name)

                    if form.is_valid():
                        fechapost = datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date()
                        cabbitacora = BitacoraActividadEstudiantePpp.objects.get(pk=int(encrypt(request.POST['id'])))
                        if fechapost >= cabbitacora.fechaini.date() and fechapost <= cabbitacora.fechafin.date():
                            detallebitacora = DetalleBitacoraEstudiantePpp(bitacorapractica=cabbitacora,
                                                                         titulo=form.cleaned_data['titulo'],
                                                                         fecha=request.POST['fecha'],
                                                                         horainicio=form.cleaned_data['hora'],
                                                                         horafin=form.cleaned_data['horafin'],
                                                                         descripcion=u'%s' % form.cleaned_data['descripcion'],
                                                                         # resultado=u'%s' % form.cleaned_data['resultado'],
                                                                         link=form.cleaned_data['link'],
                                                                         archivo=newfile)
                            detallebitacora.save(request)
                            if 'tipo' in request.POST:
                                detallebitacora.tipo = form.cleaned_data['tipo']
                            if 'rol' in request.POST:
                                detallebitacora.rol = form.cleaned_data['rol']
                            detallebitacora.save(request)
                            log(u'Adicionó bitácora de actividades prácticas %s' % (detallebitacora), request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Favor ingresar una fecha que se encuentre en el mes de " + str(nombremes(fecha=cabbitacora.fechaini.date()))}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editbitacorappp':
            try:
                detallebitacora = DetalleBitacoraEstudiantePpp.objects.get(pk=int(encrypt(request.POST['iddet'])))
                f = BitacoraActividadPppForm(request.POST)
                cabbitacora = detallebitacora.bitacorapractica
                fechapost = datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date()
                hi = request.POST['hora'] if 'hora' in request.POST else ''
                hf = request.POST['horafin'] if 'horafin' in request.POST else ''
                if not fechapost >= cabbitacora.fechaini.date() and fechapost <= cabbitacora.fechafin.date():
                    return JsonResponse({"result": True, "mensaje": u"Favor ingresar una fecha que se encuentre en el mes de " + str(nombremes(fecha=cabbitacora.fechaini.date()))}, safe=False)
                if not hi:
                    return JsonResponse({"result": "bad", "mensaje": "Seleccione la hora de inicio de la actividad."})
                if hf <= hi:
                    return JsonResponse({"result": "bad", "mensaje": "Hora fin no puede ser menor o igual a hora inicio."})
                if hi and hf:
                    h1 = timedelta(hours=int(hi.split(':')[0]), minutes=int(hi.split(':')[1]))
                    h2 = timedelta(hours=int(hf.split(':')[0]), minutes=int(hf.split(':')[1]))
                    total = f"{h2 - h1}"
                    if int(total.split(':')[0]) == 0 and int(total.split(':')[1]) < 59:
                        return JsonResponse({"result": "bad", "mensaje": "La duración de la actividad debe ser mayor a 59 minutos."})
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 20971520:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            newfile._name = generar_nombre("bitacora", newfile._name)

                if f.is_valid():
                    detallebitacora.titulo = f.cleaned_data['titulo']
                    detallebitacora.fecha = f.cleaned_data['fecha']
                    detallebitacora.horainicio = f.cleaned_data['hora']
                    detallebitacora.horafin = f.cleaned_data['horafin']
                    detallebitacora.descripcion = f.cleaned_data['descripcion']
                    if 'tipo' in request.POST:
                        detallebitacora.tipo = f.cleaned_data['tipo']
                    if 'rol' in request.POST:
                        detallebitacora.rol = f.cleaned_data['rol']
                    detallebitacora.link = f.cleaned_data['link']
                    if newfile:
                        detallebitacora.archivo = newfile
                    if detallebitacora.estadoaprobacion == 3:
                        detallebitacora.estadoaprobacion = 1
                        BitacoraActividadEstudiantePpp.objects.filter(pk=detallebitacora.bitacorapractica.id).update(estadorevision=2, persona_id=1, fecha_modificacion=datetime.now())
                    detallebitacora.save(request)
                    log(u'Editó bitácora de actividades prácticas %s' % (detallebitacora), request, "edit")
                    messages.success(request, 'Registro editado con éxito.')
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'deletedetallebitacora':
            try:
                registro = DetalleBitacoraEstudiantePpp.objects.get(id=request.POST['id'], status=True)
                registro.status=False
                registro.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'solicitarrevisionbitacora':
            try:
                bitacora = BitacoraActividadEstudiantePpp.objects.get(pk=request.POST.get('pk'))
                bitacora.estadorevision = 2
                bitacora.save(request, update_fields=['estadorevision'])
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'Error de conexión. {ex=}'})

        elif action == 'editdiscapacidad':
            try:
                data['tab'] = tab = int(request.POST.get('tab', 0))
                data['idins'] = ids = int(request.POST['idins'])
                if 'archivocarnet' in request.FILES:
                    arch = request.FILES['archivocarnet']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                if 'archivovaloracion' in request.FILES:
                    arch = request.FILES['archivovaloracion']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                persona = request.session['persona']
                f = DiscapacidadSaludForm(request.POST, request.FILES)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                newfile = None
                if not f.cleaned_data['tienediscapacidad'] and f.cleaned_data['tienediscapacidadmultiple']:
                    raise NameError('No puede marcar discapacidad multiple sin marcar que tiene discapacidad')
                if not f.cleaned_data['tipodiscapacidad'] and f.cleaned_data['tipodiscapacidadmultiple']:
                    raise NameError(
                        'No puede elegir discapacidades multiples sin elegir una discapacidad principal')
                if f.cleaned_data['tienediscapacidadmultiple'] and not f.cleaned_data['tipodiscapacidadmultiple']:
                    raise NameError('Debe elegir una o más discapacidades multiples')
                perfil = persona.mi_perfil()
                perfil.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                perfil.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                perfil.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] else 0
                perfil.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                perfil.institucionvalida = f.cleaned_data['institucionvalida']
                perfil.tienediscapacidadmultiple = f.cleaned_data['tienediscapacidadmultiple']
                perfil.grado = f.cleaned_data['grado'] if f.cleaned_data['grado'] else 0

                if 'archivocarnet' in request.FILES:
                    newfile = request.FILES['archivocarnet']
                    newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                    if not perfil.archivo or not perfil.estadoarchivodiscapacidad or perfil.estadoarchivodiscapacidad in [1, 3, 4]:
                        perfil.archivo = newfile
                        perfil.estadoarchivodiscapacidad = 1
                    if pdiscapacidad := PerfilInscripcionExtensionSalud.objects.filter(status=True, perfilinscripcion=perfil).first():
                        if newfile:
                            # if pdiscapacidad.estadoaprobacion != 2:
                            pdiscapacidad.archivodiscapacidad = newfile
                            pdiscapacidad.fecha = hoy
                            pdiscapacidad.estadoaprobacion = 1
                            pdiscapacidad.observacion = 'Actualizado por el estudiante'
                    else:
                        pdiscapacidad = PerfilInscripcionExtensionSalud(perfilinscripcion=perfil, fecha=hoy, archivodiscapacidad=newfile)
                    pdiscapacidad.save(request)
                    h = HistorialDocumentosPPPSalud(personaperfilext=pdiscapacidad, tipo=2, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion=pdiscapacidad.observacion)
                    h.save(request)
                    h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    log(u'Actualizó archivo de discapacidad salud: %s' % pdiscapacidad, request, "edit")

                if 'archivovaloracion' in request.FILES:
                    newfile = request.FILES['archivovaloracion']
                    newfile._name = generar_nombre("archivovaloracionmedica_", newfile._name)
                    perfil.archivovaloracion = newfile

                if not f.cleaned_data['tienediscapacidad']:
                    perfil.archivo = None
                    perfil.estadoarchivodiscapacidad = None
                    perfil.archivovaloracion = None

                perfil.save(request)
                perfil.tipodiscapacidadmultiple.clear()
                perfil.subtipodiscapacidad.clear()
                if f.cleaned_data['tienediscapacidadmultiple']:
                    tipos = request.POST.getlist('tipodiscapacidadmultiple')
                    for tipo in tipos:
                        perfil.tipodiscapacidadmultiple.add(tipo)
                if f.cleaned_data['tipodiscapacidad'] and f.cleaned_data['tienediscapacidad']:
                    subtipos = request.POST.getlist('subtipodiscapacidad')
                    for subtipo in subtipos:
                        perfil.subtipodiscapacidad.add(subtipo)
                log(u'Modifico tipo de discapacidad: %s' % perfil, request, "edit")
                return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                # return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos {ex}'})

        elif action == 'actualizarrequisito':
            try:
                data['tab'] = tab = int(request.POST.get('tab', 0))
                data['idins'] = ids = int(request.POST['idins'])
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() in ['pdf']:
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                persona = request.session['persona']
                f = RequisitoPPPSaludForm(request.POST, request.FILES)
                requisito = persona.requisitopracticappsalud_set.filter(status=True).first()

                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})

                if not requisito:
                    requisito = RequisitoPracticappSalud(persona=persona, observacion=request.POST['observacion'], fecha=hoytime)
                    requisito.save(request)
                else:
                    requisito.observacion = request.POST['observacion']
                    requisito.fecha = hoytime
                    requisito.save(request)

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("requisitos_practicas_salud_", newfile._name)
                    requisito.archivo = newfile
                    requisito.save(request)

                    h = HistorialDocumentosPPPSalud(personarequisito=requisito, tipo=6, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion=requisito.observacion)
                    h.save(request)
                    h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                log(u'Actualizó requisitos de practicas salud: %s' % requisito, request, "edit")
                messages.success(request, 'Registro actualizado con éxito.')
                return JsonResponse({"result": False, 'mensaje': 'Guardado con éxito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos {ex}'})

        elif action == 'delrequisito':
            try:
                with transaction.atomic():
                    requisito = RequisitoPracticappSalud.objects.get(pk=int(encrypt(request.POST['id'])))
                    requisito.status = False
                    requisito.save(request)
                    log(u'Elimino registro de requisitos para practicas : %s' % requisito, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addenfermedad':
            with transaction.atomic():
                try:
                    data['tab'] = tab = int(request.POST.get('tab', 0))
                    data['idins'] = ids = int(request.POST['idins'])
                    form = PersonaEnfermedadSaludForm(request.POST, request.FILES)
                    if not form.is_valid():
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                    if PersonaEnfermedad.objects.filter(persona=persona, enfermedad=form.cleaned_data['enfermedad'],
                                                        status=True).exists():
                        raise NameError(u"Enfermedad seleccionada ya se encuentra registrada.")
                    personaenfermedad = PersonaEnfermedad(persona=persona, enfermedad=form.cleaned_data['enfermedad'])
                    personaenfermedad.save(request)
                    if 'archivoenfermedad' in request.FILES:
                        newfile = request.FILES['archivoenfermedad']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 2194304:
                            raise NameError(u"El tamaño del archivo es mayor a 2 Mb.")
                        if not exte.lower() in ['pdf']:
                            raise NameError(u"Solo archivos .pdf,.jpg, .jpeg")
                        newfile._name = generar_nombre(str(elimina_tildes(personaenfermedad.enfermedad)), newfile._name)
                        personaenfermedad.archivomedico = newfile
                        personaenfermedad.save(request)
                        #Adiciona discapacidad para salud
                        penfermedad = PersonaEnfermedadExtensionSalud(personaenfermedad=personaenfermedad, fecha=hoy, archivoenfermedad=newfile, observacion=f'Registrado por el estudiante: {personaenfermedad.enfermedad}')
                        penfermedad.save(request)
                        h = HistorialDocumentosPPPSalud(personaenfermedadext=penfermedad, tipo=3, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion=f'Registrado por el estudiante: {personaenfermedad.enfermedad}')
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                        log(u'Actualizó archivo de discapacidad salud: %s' % penfermedad, request, "edit")
                    log(u'Adiciono enfermedad: %s' % personaenfermedad, request, "addenfermedad")
                    return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        elif action == 'editenfermedad':
            try:
                with transaction.atomic():
                    data['tab'] = tab = int(request.POST.get('tab', 0))
                    data['idins'] = ids = int(request.POST['idins'])
                    personaenfermedad = PersonaEnfermedad.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = PersonaEnfermedadSaludForm(request.POST, request.FILES)
                    if form.is_valid():
                        if PersonaEnfermedad.objects.filter(persona=persona, enfermedad=form.cleaned_data['enfermedad'],
                                                            status=True).exclude(id=personaenfermedad.id).exists():
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": True, "mensaje": "Enfermedad seleccionada ya se encuentra registrada."},
                                safe=False)
                        personaenfermedad.enfermedad = form.cleaned_data['enfermedad']
                        personaenfermedad.save(request)
                        if 'archivoenfermedad' in request.FILES:
                            newfile = request.FILES['archivoenfermedad']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 2194304:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                            if not exte.lower() in ['pdf']:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                            newfile._name = generar_nombre(str(personaenfermedad.enfermedad), newfile._name)

                            if not personaenfermedad.archivomedico or not personaenfermedad.estadoarchivo or personaenfermedad.estadoarchivo in [1, 3, 4]:
                                personaenfermedad.archivo = newfile
                                personaenfermedad.estadoarchivo = 1
                            # Actualiza discapacidad para salud
                            if penfermedad := PersonaEnfermedadExtensionSalud.objects.filter(status=True, personaenfermedad=personaenfermedad).first():
                                if newfile:
                                    # if penfermedad.estadoaprobacion != 2:
                                    penfermedad.archivoenfermedad = newfile
                                    penfermedad.estadoaprobacion = 1
                                    penfermedad.fecha = hoy
                                    penfermedad.observacion = f'Actualizado por el estudiante: {personaenfermedad.enfermedad}'
                            else:
                                penfermedad = PersonaEnfermedadExtensionSalud(personaenfermedad=personaenfermedad, fecha=hoy, archivoenfermedad=newfile, observacion=f'Actualizado por el estudiante: {personaenfermedad.enfermedad}')
                            penfermedad.save(request)
                            h = HistorialDocumentosPPPSalud(personaenfermedadext=penfermedad, tipo=3, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion=penfermedad.observacion)
                            h.save(request)
                            h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                            log(u'Actualizó archivo de discapacidad salud: %s' % persona, request, "edit")
                        log(u'Edicion de enfermedad de persona: %s' % personaenfermedad, request, "editenfermedad")
                        return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete todos los campos vacios."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delenfermedad':
            try:
                with transaction.atomic():
                    enfermedad = PersonaEnfermedad.objects.get(pk=int(encrypt(request.POST['id'])))
                    enfermedad.status = False
                    enfermedad.save(request)
                    if penfermedad := PersonaEnfermedadExtensionSalud.objects.filter(status=True, personaenfermedad=enfermedad).first():
                        penfermedad.status = False
                        penfermedad.save(request)
                        h = HistorialDocumentosPPPSalud(personaenfermedadext=penfermedad, tipo=3, fecha=hoytime, persona=persona, observacion='Registro eliminado por el estudiante')
                        h.save(request)
                        log(u'Elimino archivo de enfermedad salud: %s' % penfermedad, request, "del")
                    log(u'Elimino registro de enfermedad : %s' % enfermedad, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addembarazo':
            try:
                data['tab'] = tab = int(request.POST.get('tab', 0))
                data['idins'] = ids = int(request.POST['idins'])
                f = PersonaDetalleMaternidadSaludForm(request.POST, request.FILES)
                if not f.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
                embarazo = PersonaDetalleMaternidad(persona=persona,
                                                    gestacion=f.cleaned_data['gestacion'],
                                                    semanasembarazo=f.cleaned_data['semanasembarazo'],
                                                    lactancia=f.cleaned_data['lactancia'],
                                                    fechaparto=f.cleaned_data['fechaparto'],
                                                    fechainicioembarazo=f.cleaned_data['fechainicioembarazo'],
                                                    status_gestacion=f.cleaned_data['gestacion'],
                                                    status_lactancia=f.cleaned_data['lactancia'])
                embarazo.save(request)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 2194304:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                    if not exte.lower() in ['pdf']:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    newfile._name = generar_nombre(str(embarazo.persona), newfile._name)
                    # Actualiza discapacidad para salud
                    pembarazo = PersonaDetalleMaternidadExtensionSalud(personamaternidad=embarazo, fecha=hoy, archivoembarazo=newfile, observacion='Registrado por el estudiante')
                    pembarazo.save(request)
                    h = HistorialDocumentosPPPSalud(personamaternidadext=pembarazo, tipo=4, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion='Registrado por el estudiante')
                    h.save(request)
                    h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    log(u'Actualizó archivo de embarazo salud: %s' % pembarazo, request, "edit")
                log(u'Adiciono embarazo: %s' % embarazo, request, "add")
                return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex}'})

        elif action == 'editembarazo':
            try:
                data['tab'] = tab = int(request.POST.get('tab', 0))
                data['idins'] = ids = int(request.POST['idins'])
                f = PersonaDetalleMaternidadSaludForm(request.POST, request.FILES)
                embarazo = PersonaDetalleMaternidad.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid():
                    embarazo.persona=persona
                    embarazo.gestacion=f.cleaned_data['gestacion']
                    embarazo.semanasembarazo=f.cleaned_data['semanasembarazo']
                    embarazo.lactancia=f.cleaned_data['lactancia']
                    embarazo.fechaparto=f.cleaned_data['fechaparto']
                    embarazo.fechainicioembarazo=f.cleaned_data['fechainicioembarazo']
                    embarazo.status_gestacion=f.cleaned_data['gestacion']
                    embarazo.status_lactancia=f.cleaned_data['lactancia']
                    embarazo.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 2194304:
                            transaction.set_rollback(True)
                            return JsonResponse( {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                        if not exte.lower() in ['pdf']:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                        newfile._name = generar_nombre(str(embarazo.persona), newfile._name)
                        # Actualiza discapacidad para salud
                        if pembarazo := PersonaDetalleMaternidadExtensionSalud.objects.filter(status=True, personamaternidad=embarazo).first():
                            if newfile:
                                if pembarazo.estadoaprobacion != 2:
                                    pembarazo.archivoembarazo = newfile
                                    pembarazo.estadoaprobacion = 1
                                    pembarazo.observacion = 'Actualizado por el estudiante'
                        else:
                            pembarazo = PersonaDetalleMaternidadExtensionSalud(personamaternidad=embarazo, fecha=hoy, archivoembarazo=newfile, observacion='Actualizado por el estudiante')
                        pembarazo.save(request)
                        h = HistorialDocumentosPPPSalud(personamaternidadext=pembarazo, tipo=4, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion=pembarazo.observacion)
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                        log(u'Actualizó archivo de embarazo salud: %s' % pembarazo, request, "edit")
                    log(u'editó embarazo: %s' % embarazo, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex}'})

        elif action == 'delembarazo':
            try:
                embarazo = PersonaDetalleMaternidad.objects.get(pk=int(encrypt(request.POST['id'])))
                embarazo.status = False
                embarazo.save(request)
                if pembarazo := PersonaDetalleMaternidadExtensionSalud.objects.filter(status=True, personamaternidad=embarazo).first():
                    pembarazo.status = False
                    pembarazo.save(request)
                    h = HistorialDocumentosPPPSalud(personamaternidadext=pembarazo, tipo=4, fecha=hoytime, persona=persona, observacion='Eliminado por el estudiante')
                    h.save(request)
                    log(u'Elimino archivo embarazo salud: %s' % pembarazo, request, "del")
                log(u'Elimino embarazo: %s' % embarazo, request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addfamiliar':
            try:
                data['tab'] = tab = int(request.POST.get('tab', 0))
                data['idins'] = ids = int(request.POST['idins'])
                persona = request.session['persona']
                f = FamiliarSaludForm(request.POST)
                if f.is_valid():
                    edit_d = eval(request.POST.get('edit_d', ''))
                    cedula = f.cleaned_data['identificacion'].strip()
                    if persona.personadatosfamiliares_set.filter(identificacion=f.cleaned_data['identificacion'], status=True).exists():
                        raise NameError('El familiar se encuentra registrado.')
                    nombres = f"{f.cleaned_data['apellido1']} {f.cleaned_data['apellido2']} {f.cleaned_data['nombre']}"
                    familiar = PersonaDatosFamiliares(persona=persona,
                                                      identificacion=cedula,
                                                      nombre=nombres,
                                                      fallecido=f.cleaned_data['fallecido'],
                                                      nacimiento=f.cleaned_data['nacimiento'],
                                                      parentesco=f.cleaned_data['parentesco'],
                                                      tienediscapacidad=f.cleaned_data['tienediscapacidad'],
                                                      telefono=f.cleaned_data['telefono'],
                                                      telefono_conv=f.cleaned_data['telefono_conv'],
                                                      niveltitulacion=f.cleaned_data['niveltitulacion'],
                                                      ingresomensual=f.cleaned_data['ingresomensual'],
                                                      formatrabajo=f.cleaned_data['formatrabajo'],
                                                      trabajo=f.cleaned_data['trabajo'],
                                                      convive=f.cleaned_data['convive'],
                                                      sustentohogar=f.cleaned_data['sustentohogar'],
                                                      essustituto=f.cleaned_data['essustituto'],
                                                      autorizadoministerio=f.cleaned_data['autorizadoministerio'],
                                                      tipodiscapacidad=f.cleaned_data['tipodiscapacidad'],
                                                      porcientodiscapacidad=f.cleaned_data['porcientodiscapacidad'],
                                                      carnetdiscapacidad=f.cleaned_data['carnetdiscapacidad'],
                                                      institucionvalida=f.cleaned_data['institucionvalida'],
                                                      tipoinstitucionlaboral=f.cleaned_data['tipoinstitucionlaboral'],
                                                      negocio=f.cleaned_data['negocio'],
                                                      esservidorpublico=f.cleaned_data['esservidorpublico'],
                                                      bajocustodia=f.cleaned_data['bajocustodia'],
                                                      centrocuidado=f.cleaned_data['centrocuidado'] if f.cleaned_data['centrocuidado'] else 0,
                                                      centrocuidadodesc=f.cleaned_data['centrocuidadodesc'],
                                                      tienenegocio=f.cleaned_data['tienenegocio'])
                    familiar.save(request)
                    banninio, bandiscapacidad, banenfermedad = False, False, False
                    if 'cedulaidentidad' in request.FILES:
                        newfile = request.FILES['cedulaidentidad']
                        newfile._name = generar_nombre("cedulaidentidad_", newfile._name)
                        familiar.cedulaidentidad = newfile
                        familiar.save(request)
                        banninio = True
                    if 'ceduladiscapacidad' in request.FILES: #considerado para validar discapacidad
                        newfile = request.FILES['ceduladiscapacidad']
                        newfile._name = generar_nombre("ceduladiscapacidad_", newfile._name)
                        familiar.ceduladiscapacidad = newfile
                        familiar.save(request)
                        bandiscapacidad = True
                    if 'archivoautorizado' in request.FILES: #considerado para validar discapacidad y enfermedad (sustituto)
                        newfile = request.FILES['archivoautorizado']
                        newfile._name = generar_nombre("archivoautorizado_", newfile._name)
                        familiar.archivoautorizado = newfile
                        familiar.save(request)
                        bandiscapacidad, banenfermedad = True, True
                    if 'cartaconsentimiento' in request.FILES:
                        newfile = request.FILES['cartaconsentimiento']
                        newfile._name = generar_nombre(f"cartaconsentimiento_{persona.usuario.username}", newfile._name)
                        familiar.cartaconsentimiento = newfile
                        familiar.save(request)
                    if 'archivocustodia' in request.FILES:
                        newfile = request.FILES['archivocustodia']
                        newfile._name = generar_nombre(f"archivocustodia_{persona.usuario.username}", newfile._name)
                        familiar.archivocustodia = newfile
                        familiar.save(request)
                        banninio = True
                    pfamiliarext = PersonaDatosFamiliaresExtensionSalud(personafamiliar=familiar)
                    pfamiliarext.save(request)
                    log(u'Adiciono extension familiar: %s' % pfamiliarext, request, "add")
                    if banninio and familiar.obtener_edad() < 5:
                        h = HistorialDocumentosPPPSalud(personafamiliarext=pfamiliarext, tipo=5, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion='Registrado por el estudiante')
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    if bandiscapacidad and familiar.tienediscapacidad:
                        h = HistorialDocumentosPPPSalud(personafamiliarext=pfamiliarext, tipo=31, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion='Registrado por el estudiante')
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    # para guaradr el historia es necesario tener la enfermedad, no se puede capturar aqui
                    # if banenfermedad and pfamiliarext.listado_enfermedades():
                    #     h = HistorialDocumentosPPPSalud(personafamiliarext=pfamiliarext, tipo=3, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion='Registrado por el estudiante')
                    #     h.save(request)

                    pers = Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS' + cedula)) | Q(cedula=cedula[2:]),status=True).first()
                    if not pers:
                        pers = Persona(cedula=f.cleaned_data['identificacion'],
                                       nombres=f.cleaned_data['nombre'],
                                       apellido1=f.cleaned_data['apellido1'],
                                       apellido2=f.cleaned_data['apellido2'],
                                       nacimiento=f.cleaned_data['nacimiento'],
                                       telefono=f.cleaned_data['telefono'],
                                       sexo=f.cleaned_data['sexo'],
                                       telefono_conv=f.cleaned_data['telefono_conv'],
                                       )
                        pers.save(request)
                        log(u'Adiciono persona: %s' % persona, request, "add")
                    elif len(pers.mis_perfilesusuarios()) == 1 and pers.tiene_usuario_externo():
                        pers.telefono = f.cleaned_data['telefono']
                        pers.sexo = f.cleaned_data['sexo']
                        pers.telefono_conv = f.cleaned_data['telefono_conv']
                        pers.save(request)
                        log(u'Edito familiar de usuario: %s' % pers, request, "edit")
                    if not pers.tiene_perfil():
                        if not Externo.objects.filter(persona=pers, status=True):
                            externo = Externo(persona=pers)
                            externo.save(request)
                            log(u'Adiciono externo: %s' % pers, request, "add")
                        perfil = PerfilUsuario(persona=pers, externo=externo)
                        perfil.save(request)
                        log(u'Adiciono perfil de usuario: %s' % perfil, request, "add")

                    perfil_i = pers.mi_perfil()
                    if not edit_d and perfil_i.tienediscapacidad:
                        familiar.tienediscapacidad=perfil_i.tienediscapacidad
                        familiar.tipodiscapacidad=perfil_i.tipodiscapacidad
                        familiar.porcientodiscapacidad=perfil_i.porcientodiscapacidad
                        familiar.carnetdiscapacidad=perfil_i.carnetdiscapacidad
                        familiar.institucionvalida=perfil_i.institucionvalida
                        familiar.ceduladiscapacidad=perfil_i.archivo.name if perfil_i.archivo else ''
                        familiar.archivoautorizado=perfil_i.archivovaloracion.name if perfil_i.archivovaloracion else ''
                    elif f.cleaned_data['tienediscapacidad']:
                        perfil_i.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                        perfil_i.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                        perfil_i.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] else 0
                        perfil_i.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                        perfil_i.institucionvalida = f.cleaned_data['institucionvalida']
                        if 'ceduladiscapacidad' in request.FILES:
                            newfile = request.FILES['ceduladiscapacidad']
                            newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                            perfil_i.archivo = newfile
                            perfil_i.estadoarchivodiscapacidad = 1
                        if 'archivoautorizado' in request.FILES:
                            newfile = request.FILES['archivoautorizado']
                            newfile._name = generar_nombre("archivovaloracionmedica_", newfile._name)
                            perfil_i.archivovaloracion = newfile
                        perfil_i.save(request)
                    if f.cleaned_data['parentesco'].id in [14,11] and not persona.apellido1 in [pers.apellido1,pers.apellido2]:
                        familiar.aprobado=False
                    if f.cleaned_data['parentesco'].id == 13 and not pers.personadatosfamiliares_set.filter(personafamiliar=persona, status=True).exists():
                        fam_ = PersonaDatosFamiliares(persona=pers,
                                                      personafamiliar=persona,
                                                      identificacion=persona.cedula,
                                                      nombre=persona.nombre_completo_inverso(),
                                                      nacimiento=persona.nacimiento,
                                                      parentesco=f.cleaned_data['parentesco'],
                                                      telefono=persona.telefono,
                                                      telefono_conv=persona.telefono_conv,
                                                      convive=f.cleaned_data['convive'])
                        fam_.save(request)
                        perfil_fam = persona.mi_perfil()
                        if perfil_fam.tienediscapacidad:
                            fam_.tienediscapacidad = perfil_fam.tienediscapacidad
                            fam_.tipodiscapacidad = perfil_fam.tipodiscapacidad
                            fam_.porcientodiscapacidad = perfil_fam.porcientodiscapacidad
                            fam_.carnetdiscapacidad = perfil_fam.carnetdiscapacidad
                            fam_.institucionvalida = perfil_fam.institucionvalida
                            fam_.ceduladiscapacidad = perfil_fam.archivo.name if perfil_i.archivo else ''
                            fam_.archivoautorizado = perfil_fam.archivovaloracion.name if perfil_i.archivovaloracion else ''
                        fam_.save(request)
                    familiar.personafamiliar=pers
                    familiar.save(request)
                    if familiar.parentesco.id in [11, 14] or familiar.bajocustodia:
                        per_extension = persona.personaextension_set.filter(status=True).first()
                        hijos = per_extension.hijos if per_extension.hijos else 0
                        per_extension.hijos = hijos+1
                        per_extension.save(request)
                    log(u'Adiciono familiar: %s' % familiar, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex}'})

        elif action == 'editfamiliar':
            try:
                data['tab'] = tab = int(request.POST.get('tab', 0))
                data['idins'] = ids = int(request.POST['idins'])
                persona = request.session['persona']
                f = FamiliarSaludForm(request.POST)
                f.edit()
                if f.is_valid():
                    familiar = PersonaDatosFamiliares.objects.get(pk=int(encrypt(request.POST['id'])))
                    edit_d=eval(request.POST.get('edit_d',''))
                    cedula = f.cleaned_data['identificacion'].strip()
                    if persona.personadatosfamiliares_set.filter(identificacion=cedula, status=True).exclude(id=familiar.id).exists():
                        raise NameError(u'El familiar se encuentra registrado.')
                    nombres = f"{f.cleaned_data['apellido1']} {f.cleaned_data['apellido2']} {f.cleaned_data['nombre']}"
                    pers = Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS' + cedula)) | Q(cedula=cedula[2:]),status=True).first()
                    familiar.fallecido = f.cleaned_data['fallecido']
                    familiar.parentesco = f.cleaned_data['parentesco']
                    familiar.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                    familiar.trabajo = f.cleaned_data['trabajo']
                    familiar.niveltitulacion = f.cleaned_data['niveltitulacion']
                    familiar.ingresomensual = f.cleaned_data['ingresomensual']
                    familiar.formatrabajo = f.cleaned_data['formatrabajo']
                    familiar.convive = f.cleaned_data['convive']
                    familiar.sustentohogar = f.cleaned_data['sustentohogar']
                    familiar.tienenegocio = f.cleaned_data['tienenegocio']
                    familiar.esservidorpublico = f.cleaned_data['esservidorpublico']
                    familiar.bajocustodia = f.cleaned_data['bajocustodia']
                    familiar.centrocuidado = f.cleaned_data['centrocuidado'] if f.cleaned_data['centrocuidado'] else 0
                    familiar.centrocuidadodesc = f.cleaned_data['centrocuidadodesc']
                    familiar.negocio = ''
                    familiar.tipoinstitucionlaboral = f.cleaned_data['tipoinstitucionlaboral']
                    if familiar.tienenegocio:
                        familiar.negocio = f.cleaned_data['negocio']
                    familiar.save(request)
                    #Seleciona o agrega el registro para validacion de salud
                    banninio, bandiscapacidad, banenfermedad = False, False, False
                    pfamiliarext = PersonaDatosFamiliaresExtensionSalud.objects.filter(personafamiliar=familiar, status=True).first()
                    if not pfamiliarext:
                        pfamiliarext = PersonaDatosFamiliaresExtensionSalud(personafamiliar=familiar)
                        pfamiliarext.save(request)
                        log(u'Adiciono extension familiar: %s' % pfamiliarext, request, "add")
                    if 'cedulaidentidad' in request.FILES:
                        newfile = request.FILES['cedulaidentidad']
                        newfile._name = generar_nombre("cedulaidentidad_", newfile._name)
                        familiar.cedulaidentidad = newfile
                        familiar.save(request)
                        banninio = True
                    if 'ceduladiscapacidad' in request.FILES:
                        newfile = request.FILES['ceduladiscapacidad']
                        newfile._name = generar_nombre("ceduladiscapacidad_", newfile._name)
                        familiar.ceduladiscapacidad = newfile
                        familiar.save(request)
                        pfamiliarext.estadoaprobaciondiscapacidad = 1
                        pfamiliarext.save(request)
                        bandiscapacidad = True
                    if 'cartaconsentimiento' in request.FILES:
                        newfile = request.FILES['cartaconsentimiento']
                        newfile._name = generar_nombre(f"cartaconsentimiento_{persona.usuario.username}", newfile._name)
                        familiar.cartaconsentimiento = newfile
                        familiar.save(request)
                    if 'archivocustodia' in request.FILES:
                        newfile = request.FILES['archivocustodia']
                        newfile._name = generar_nombre(f"archivocustodia_{persona.usuario.username}", newfile._name)
                        familiar.archivocustodia = newfile
                        familiar.save(request)
                        banninio = True
                    if 'archivoautorizado' in request.FILES:
                        newfile = request.FILES['archivoautorizado']
                        newfile._name = generar_nombre("archivoautorizado_", newfile._name)
                        familiar.archivoautorizado = newfile
                        familiar.save(request)
                        bandiscapacidad, banenfermedad = True, True

                    if banninio and familiar.obtener_edad() < 5:
                        pfamiliarext.estadoaprobacionninio = 1
                        pfamiliarext.save(request)
                        h = HistorialDocumentosPPPSalud(personafamiliarext=pfamiliarext, tipo=5, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion='Actualizado por el estudiante')
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    if bandiscapacidad and familiar.tienediscapacidad:
                        pfamiliarext.estadoaprobaciondiscapacidad = 1
                        pfamiliarext.save(request)
                        h = HistorialDocumentosPPPSalud(personafamiliarext=pfamiliarext, tipo=31, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion='Actualizado por el estudiante')
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    # if banenfermedad and pfamiliarext.listado_enfermedades() and pfamiliarext.cantidad_enfermedades_aprobadas() == 0:
                    #     pfamiliarext.estadoaprobacionenfermedad = 1
                    #     pfamiliarext.save(request)
                    #     h = HistorialDocumentosPPPSalud(personafamiliarext=pfamiliarext, tipo=3, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion='Actualizado por el estudiante')
                    #     h.save(request)
                    log(u'Adiciono extension familiar: %s' % pfamiliarext, request, "add")

                    if not pers:
                        pers = Persona(cedula=f.cleaned_data['identificacion'],
                                       nombres=f.cleaned_data['nombre'],
                                       apellido1=f.cleaned_data['apellido1'],
                                       apellido2=f.cleaned_data['apellido2'],
                                       nacimiento=f.cleaned_data['nacimiento'],
                                       telefono=f.cleaned_data['telefono'],
                                       sexo=f.cleaned_data['sexo'],
                                       telefono_conv=f.cleaned_data['telefono_conv'],
                                       )
                        pers.save(request)
                        log(u'Adiciono persona: %s' % persona, request, "add")
                    elif len(pers.mis_perfilesusuarios()) == 1 and pers.tiene_usuario_externo():
                        pers.cedula = cedula
                        pers.nombres = f.cleaned_data['nombre']
                        pers.apellido1 = f.cleaned_data['apellido1']
                        pers.apellido2 = f.cleaned_data['apellido2']
                        pers.nacimiento = f.cleaned_data['nacimiento']
                        pers.telefono = f.cleaned_data['telefono']
                        pers.sexo = f.cleaned_data['sexo']
                        pers.telefono_conv = f.cleaned_data['telefono_conv']
                        pers.save(request)
                        log(u'Edito familiar de usuario: %s' % pers, request, "edit")
                    if not pers.tiene_perfil():
                        if not Externo.objects.filter(persona=pers, status=True):
                            externo = Externo(persona=pers)
                            externo.save(request)
                            log(u'Adiciono externo: %s' % pers, request, "add")
                        perfil = PerfilUsuario(persona=pers, externo=externo)
                        perfil.save(request)
                        log(u'Adiciono perfil de usuario: %s' % perfil, request, "add")
                    if len(pers.mis_perfilesusuarios()) == 1 and pers.tiene_usuario_externo():
                        familiar.identificacion = cedula
                        familiar.nombre = nombres
                        familiar.nacimiento = f.cleaned_data['nacimiento']
                        familiar.telefono = f.cleaned_data['telefono']
                        familiar.telefono_conv = f.cleaned_data['telefono_conv']
                    else:
                        familiar.identificacion = pers.cedula
                        familiar.nombre = pers.nombre_completo_inverso()
                        familiar.nacimiento = pers.nacimiento
                        familiar.telefono = pers.telefono
                        familiar.telefono_conv = pers.telefono_conv
                    perfil_i = pers.mi_perfil()
                    if edit_d:
                        if f.cleaned_data['tienediscapacidad']:
                            familiar.essustituto = f.cleaned_data['essustituto']
                            familiar.autorizadoministerio = f.cleaned_data['autorizadoministerio']
                            familiar.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                            familiar.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad']
                            familiar.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                            familiar.institucionvalida = f.cleaned_data['institucionvalida']
                            perfil_i.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                            perfil_i.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                            perfil_i.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] else 0
                            perfil_i.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                            perfil_i.institucionvalida = f.cleaned_data['institucionvalida']
                            if 'ceduladiscapacidad' in request.FILES:
                                newfile = request.FILES['ceduladiscapacidad']
                                newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                                perfil_i.archivo = newfile
                                perfil_i.estadoarchivodiscapacidad = 1
                            if 'archivoautorizado' in request.FILES:
                                newfile = request.FILES['archivoautorizado']
                                newfile._name = generar_nombre("archivovaloracionmedica_", newfile._name)
                                perfil_i.archivovaloracion = newfile
                            perfil_i.save(request)
                        else:
                            familiar.autorizadoministerio = False
                            familiar.tipodiscapacidad = None
                            familiar.porcientodiscapacidad = None
                            familiar.carnetdiscapacidad = ''
                            familiar.institucionvalida = None
                            perfil_i.tienediscapacidad = False
                            perfil_i.tipodiscapacidad = None
                            perfil_i.porcientodiscapacidad = None
                            perfil_i.carnetdiscapacidad = ''
                            perfil_i.institucionvalida = None
                            perfil_i.save(request)
                    elif perfil_i.tienediscapacidad:
                        familiar.essustituto = f.cleaned_data['essustituto']
                        familiar.autorizadoministerio = f.cleaned_data['autorizadoministerio']
                        familiar.tienediscapacidad = perfil_i.tienediscapacidad
                        familiar.tipodiscapacidad = perfil_i.tipodiscapacidad
                        familiar.porcientodiscapacidad = perfil_i.porcientodiscapacidad
                        familiar.carnetdiscapacidad = perfil_i.carnetdiscapacidad
                        familiar.institucionvalida = perfil_i.institucionvalida
                        familiar.ceduladiscapacidad = perfil_i.archivo.name if perfil_i.archivo else ''
                        familiar.archivoautorizado = perfil_i.archivovaloracion.name if perfil_i.archivovaloracion else ''
                        perfil_i.save(request)
                    if f.cleaned_data['parentesco'].id in [14, 11] and not persona.apellido1 in [pers.apellido1, pers.apellido2]:
                        familiar.aprobado = False
                    if f.cleaned_data['parentesco'].id == 13 and not pers.personadatosfamiliares_set.filter(personafamiliar=persona, status=True).exists():
                        fam_ = PersonaDatosFamiliares(persona=pers,
                                                      personafamiliar=persona,
                                                      identificacion=persona.cedula,
                                                      nombre=persona.nombre_completo_inverso(),
                                                      nacimiento=persona.nacimiento,
                                                      parentesco=f.cleaned_data['parentesco'],
                                                      telefono=persona.telefono,
                                                      telefono_conv=persona.telefono_conv,
                                                      convive=f.cleaned_data['convive'])
                        fam_.save(request)
                        perfil_fam = persona.mi_perfil()
                        if perfil_fam.tienediscapacidad:
                            fam_.tienediscapacidad = perfil_fam.tienediscapacidad
                            fam_.tipodiscapacidad = perfil_fam.tipodiscapacidad
                            fam_.porcientodiscapacidad = perfil_fam.porcientodiscapacidad
                            fam_.carnetdiscapacidad = perfil_fam.carnetdiscapacidad
                            fam_.institucionvalida = perfil_fam.institucionvalida
                            fam_.ceduladiscapacidad = perfil_fam.archivo.name if perfil_i.archivo else ''
                            fam_.archivoautorizado = perfil_fam.archivovaloracion.name if perfil_i.archivovaloracion else ''
                        fam_.save(request)
                    familiar.personafamiliar = pers
                    familiar.save(request)
                    log(u'Modifico familiar: %s' % persona, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': str(ex)})

        elif action == 'actualizarfamiliarninio':
            try:
                data['tab'] = tab = int(request.POST.get('tab', 0))
                data['idins'] = ids = int(request.POST['idins'])
                persona = request.session['persona']
                f = FamiliarNinioSaludForm(request.POST)
                if f.is_valid():
                    familiar = PersonaDatosFamiliares.objects.get(pk=int(encrypt(request.POST['id'])))
                    bandera = False
                    familiar.bajocustodia = f.cleaned_data['bajocustodia']
                    familiar.parentesco = f.cleaned_data['parentesco']
                    familiar.save(request)
                    #Seleciona o agrega el registro para validacion de salud
                    pfamiliarext = PersonaDatosFamiliaresExtensionSalud.objects.filter(personafamiliar=familiar, status=True).first()
                    if not pfamiliarext:
                        pfamiliarext = PersonaDatosFamiliaresExtensionSalud(personafamiliar=familiar)
                        pfamiliarext.save(request)
                        log(u'Adiciono extension familiar: %s' % pfamiliarext, request, "add")
                    if 'cedulaidentidad' in request.FILES:
                        newfile = request.FILES['cedulaidentidad']
                        newfile._name = generar_nombre("cedulaidentidad_", newfile._name)
                        familiar.cedulaidentidad = newfile
                        bandera = True
                    if 'archivocustodia' in request.FILES:
                        newfile = request.FILES['archivocustodia']
                        newfile._name = generar_nombre(f"archivocustodia_{persona.usuario.username}", newfile._name)
                        familiar.archivocustodia = newfile
                        bandera = True
                    if bandera or familiar.bajocustodia:
                        pfamiliarext.estadoaprobacionninio = 1
                        pfamiliarext.save(request)
                        h = HistorialDocumentosPPPSalud(personafamiliarext=pfamiliarext, tipo=5, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion='Actualizado por el estudiante')
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    if not familiar.bajocustodia:
                        familiar.archivocustodia = None
                    familiar.save(request)
                    log(u'Modifico ninio familiar: %s' % persona, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': str(ex)})

        elif action == 'addfamiliarenfermedad':
            with transaction.atomic():
                try:
                    data['tab'] = tab = int(request.POST.get('tab', 0))
                    data['idins'] = ids = int(request.POST['idins'])
                    bandera = False
                    familiar = PersonaDatosFamiliares.objects.get(pk=int(encrypt(request.POST['id'])))
                    personafamiliarext = PersonaDatosFamiliaresExtensionSalud.objects.filter(personafamiliar=familiar).first()
                    if not personafamiliarext:
                        personafamiliarext = PersonaDatosFamiliaresExtensionSalud(personafamiliar=familiar)
                        personafamiliarext.save(request)
                        log(u'Adiciono extension familiar: %s' % personafamiliarext, request, "add")
                    form = FamiliarEnfermedadSaludForm(request.POST, request.FILES)
                    if not form.is_valid():
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                    if EnfermedadFamiliarSalud.objects.filter(personafamiliarext=personafamiliarext, enfermedad=form.cleaned_data['enfermedad'], status=True).exists():
                        raise NameError(u"Enfermedad seleccionada ya se encuentra registrada.")
                    familiarenfermedad = EnfermedadFamiliarSalud(personafamiliarext=personafamiliarext, fecha=hoy, enfermedad=form.cleaned_data['enfermedad'])
                    familiarenfermedad.save(request)
                    familiar.essustituto = form.cleaned_data['essustituto']
                    if 'archivoautorizado' in request.FILES:
                        newfile = request.FILES['archivoautorizado']
                        newfile._name = generar_nombre("archivoautorizado_", newfile._name)
                        familiar.archivoautorizado = newfile
                        bandera = True
                    familiar.save(request)
                    if 'archivoenfermedad' in request.FILES:
                        newfile = request.FILES['archivoenfermedad']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 2194304:
                            raise NameError(u"El tamaño del archivo es mayor a 2 Mb.")
                        if not exte.lower() in ['pdf']:
                            raise NameError(u"Solo archivos .pdf,.jpg, .jpeg")
                        newfile._name = generar_nombre(str(elimina_tildes(familiarenfermedad.enfermedad)), newfile._name)
                        familiarenfermedad.archivoenfermedad = newfile
                        familiarenfermedad.observacion = f'Registrado por el estudiante: {familiarenfermedad.enfermedad}'
                        familiarenfermedad.save(request)
                        bandera = True
                    if bandera and familiar.essustituto:
                        h = HistorialDocumentosPPPSalud(personafamiliarext=personafamiliarext, enfermedadfamiliar=familiarenfermedad, tipo=32, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion=f'Registrado por el estudiante: {familiarenfermedad.enfermedad}')
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    log(u'Adiciono enfermedad familiar: %s' % familiarenfermedad, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        elif action == 'editfamiliarenfermedad':
            with transaction.atomic():
                try:
                    data['tab'] = tab = int(request.POST.get('tab', 0))
                    data['idins'] = ids = int(request.POST['idins'])
                    bandera = False
                    familiarenfermedad = EnfermedadFamiliarSalud.objects.get(pk=int(encrypt(request.POST['id'])))
                    familiar = familiarenfermedad.personafamiliarext.personafamiliar
                    form = FamiliarEnfermedadSaludForm(request.POST, request.FILES)
                    if not form.is_valid():
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                    if EnfermedadFamiliarSalud.objects.filter(personafamiliarext=familiarenfermedad.personafamiliarext, enfermedad=form.cleaned_data['enfermedad'],
                                                              status=True).exclude(id=familiarenfermedad.id).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Enfermedad seleccionada ya se encuentra registrada."}, safe=False)
                    familiarenfermedad.enfermedad = form.cleaned_data['enfermedad']
                    familiarenfermedad.save(request)
                    familiar.essustituto = form.cleaned_data['essustituto']
                    if 'archivoautorizado' in request.FILES:
                        newfile = request.FILES['archivoautorizado']
                        newfile._name = generar_nombre("archivoautorizado_", newfile._name)
                        familiar.archivoautorizado = newfile
                        bandera = True
                    familiar.save(request)
                    if 'archivoenfermedad' in request.FILES:
                        newfile = request.FILES['archivoenfermedad']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 2194304:
                            raise NameError(u"El tamaño del archivo es mayor a 2 Mb.")
                        if not exte.lower() in ['pdf']:
                            raise NameError(u"Solo archivos .pdf,.jpg, .jpeg")
                        newfile._name = generar_nombre(str(elimina_tildes(familiarenfermedad.enfermedad)), newfile._name)
                        familiarenfermedad.estadoaprobacion = 1
                        familiarenfermedad.archivoenfermedad = newfile
                        familiarenfermedad.observacion = f'Actualizado por el estudiante: {familiarenfermedad.enfermedad}'
                        familiarenfermedad.save(request)
                        bandera = True
                    if bandera and familiar.essustituto:
                        h = HistorialDocumentosPPPSalud(personafamiliarext=familiarenfermedad.personafamiliarext, enfermedadfamiliar=familiarenfermedad, tipo=32, fecha=hoytime, estadoaprobacion=1, persona=persona, observacion=f'Actualizado por el estudiante: {familiarenfermedad.enfermedad}')
                        h.save(request)
                        h.genera_notificacion_estudiante(persona_valida, persona, encrypt(ids), tab)
                    log(u'Edito enfermedad familiar: %s' % familiarenfermedad, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Guardado con exito', 'to': "{}?action=actualizardatossalud&idalu={}&tab={}".format(request.path, encrypt(ids), tab)}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        elif action == 'delfamiliarenfermedad':
            try:
                with transaction.atomic():
                    enfermedadfamiliar = EnfermedadFamiliarSalud.objects.get(pk=int(encrypt(request.POST['id'])))
                    enfermedadfamiliar.status = False
                    enfermedadfamiliar.save(request)
                    h = HistorialDocumentosPPPSalud(personafamiliarext=enfermedadfamiliar.personafamiliarext, enfermedadfamiliar=enfermedadfamiliar, tipo=32, fecha=hoytime, persona=persona, observacion=f'Eliminado por el estudiante: {enfermedadfamiliar.enfermedad}')
                    h.save(request)
                    log(u'Elimino registro de enfermedad : %s - %s - %s', request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": True, "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'verinscripcionpracticapp':
                try:
                    data['action'] = request.GET['action']
                    data['id'] = idpreinsc = int(encrypt(request.GET['id']))
                    turno = None
                    iddetpreinsc = request.GET['idpreins'] if 'idpreins' in request.GET and int(request.GET['idpreins']) > 0 else None
                    data['detalle'] = detallepreinscripcion = DetallePreInscripcionPracticasPP.objects.get(pk=iddetpreinsc)
                    data['grupoorden'] = grupoorden = detallepreinscripcion.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if detallepreinscripcion.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
                    ofertas = []
                    # ofertas = ConfiguracionInscripcionPracticasPP.objects.filter(preinscripcion_id=idpreinsc, itinerariomalla__in=[detallepreinscripcion.itinerariomalla], estado=2, status=True)
                    if orden := detallepreinscripcion.inscripcion.ordenprioridadinscripcion_set.first():
                        data['turno'] = turno = orden.obtenerturnoinscripcion(grupoorden, detallepreinscripcion.preinscripcion)

                    # data['lectura'] = True
                    registro = PracticasPreprofesionalesInscripcion.objects.filter(itinerariomalla=detallepreinscripcion.itinerariomalla, preinscripcion_id__in=detallepreinscripcion.preinscripcion.detallepreinscripcionpracticaspp_set.values_list('id', flat=True).filter(inscripcion=detallepreinscripcion.inscripcion, status=True)).last()
                    # ofertaselecionada = []
                    if registro:
                        if historialinsc := registro.historialinscricionoferta_set.filter(status=True, ordenprioridad=turno).last():
                            ofertas = ConfiguracionInscripcionPracticasPP.objects.filter(pk=historialinsc.configinscppp.id)
                    data['ofertas'] = ofertas
                    template = get_template("alu_practicassalud/modal/inscribirpracticapp.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': 'Problemas al ejecutar la acción, intente nuevamente mas tarde.'})

            if action == 'validarturnoseleccion':
                try:
                    genero = 'a' if persona.es_mujer() else 'o'
                    data['action'] = request.GET['action']
                    data['ido'] = idoferta = int(request.GET['ido'])
                    data['id'] = idpreinsc = int(request.GET['id'])
                    validado = valida_turno_seleccion(persona, idoferta, idpreinsc)
                    return JsonResponse(validado)
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': 'Problemas al validar el turno, intente nuevamente más tarde.'})

            elif action == 'selecionarofertas':
                try:
                    data['title'] = u'Inscripcion de prácticas preprofesionales Salud'
                    data['action'] = request.GET['action']
                    data['id'] = idpreinsc = int(encrypt(request.GET['id']))
                    turno = None
                    iddetpreinsc = int(encrypt(request.GET['idpreins'])) if 'idpreins' in request.GET and int(encrypt(request.GET['idpreins'])) > 0 else None
                    data['detalle'] = detallepreinscripcion = DetallePreInscripcionPracticasPP.objects.get(pk=iddetpreinsc)
                    data['grupoorden'] = grupoorden = detallepreinscripcion.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if detallepreinscripcion.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
                    ofertas = ConfiguracionInscripcionPracticasPP.objects.filter(preinscripcion_id=idpreinsc, itinerariomalla__in=[detallepreinscripcion.itinerariomalla], estado=2, fechainiciooferta__lte=hoy, fechafinoferta__gte=hoy, status=True)
                    if orden := detallepreinscripcion.inscripcion.ordenprioridadinscripcion_set.first():
                        data['turno'] = turno = orden.obtenerturnoinscripcion(grupoorden, detallepreinscripcion.preinscripcion)
                    if detallepreinscripcion.estado != 2:
                        listado = PracticasPreprofesionalesInscripcion.objects.filter(preinscripcion_id__in=detallepreinscripcion.preinscripcion.detallepreinscripcionpracticaspp_set.values_list('id', flat=True).filter(inscripcion=detallepreinscripcion.inscripcion, status=True))
                        if variable_valor('VALIDA_SELECCION_EMPRESA') and listado:  # Filtra la seleccion de una misma empresa
                            ofertas = ofertas.filter(asignacionempresapractica_id__in=list(listado.values_list('asignacionempresapractica_id', flat=True)))
                        if variable_valor('VALIDA_SELECCION_FECHA_PRACTICAS') and listado:  # Filtra la seleccion de una misma fecha de inicio de las prácticas
                            ofertas = ofertas.exclude(fechainicio__in=list(listado.values_list('fechadesde', flat=True)))
                        if variable_valor('VALIDA_SELECCION_DIA_ACADEMICO') and listado:  # Filtra la seleccion excluyendo por el dia antes seleccionado
                            listadoexten = PracticasPreprofesionalesInscripcionExtensionSalud.objects.filter(practicasppinscripcion_id__in=listado.values_list('id', flat=True))
                            ofertas = ofertas.filter(dia__in=list(listadoexten.values_list('dia', flat=True).exclude(dia=0)))
                        data['seleccionempresa'] = listado
                        data['ofertas'] = ofertas
                        data['totalofertas'] = len(ofertas)
                    return render(request, "alu_practicassaludinscripcion/viewseleccionoferta.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/alu_practicassaludinscripcion?info={}'.format(ex))

            elif action == 'seleccionasignaturaitinerario':
                try:
                    data['action'] = request.GET['action']
                    data['idconfi'] = id = int(request.GET['id'])
                    data['idturno'] = idturno = int(request.GET['idturno'])
                    data['idpreins'] = idpreins = int(request.GET['idpreins'])

                    data['oferta'] = oferta = ConfiguracionInscripcionPracticasPP.objects.get(pk=id)
                    data['detalle'] = detalle = DetallePreInscripcionPracticasPP.objects.get(pk=idpreins)
                    data['turno'] = turno = OrdenPrioridadInscripcion.objects.filter(pk=idturno).first()

                    data['asignaturas'] = eAsignaturas = ItinerarioAsignaturaSalud.objects.filter(itinerariomalla=detalle.itinerariomalla, status=True)
                    if not eAsignaturas:
                        raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, proceso de matriculación no se encuentra configurado")
                    data['materia'] = materia = eAsignaturas.first().asignaturamalla
                    data['inscripcion'] = inscripcion = detalle.inscripcion

                    ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, activo=True, tipo=2, periodo=periodo_matricular)
                    if ePeriodoMatricula:
                        if len(ePeriodoMatricula) > 1:
                            raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, proceso de matriculación no se encuentra activo")
                        ePeriodoMatricula = ePeriodoMatricula[0]
                        if not ePeriodoMatricula.esta_periodoactivomatricula():
                            raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, el periodo de matriculación se encuentra inactivo")
                        if inscripcion.tiene_perdida_carrera(ePeriodoMatricula.num_matriculas):
                            raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")

                    nivel = []
                    nivelaux = Nivel.objects.filter(nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera,
                                                    nivellibrecoordinacion__coordinacion__sede=inscripcion.sede,
                                                    modalidad=inscripcion.modalidad, cerrado=False,
                                                    fin__gte=hoy, periodo=periodo_matricular).order_by('-fin')
                    if nivelaux.exists():
                        nivel = nivelaux[0]

                    # data: {'action': 'materiasabiertas', 'ida': asignatura, 'idam': asignaturamalla, 'nivel': '{{ nivel.id }}', 'id': inscripcion},

                    matriculas = materia.cantidad_matriculas_asignatura(inscripcion)
                    programada = materia.asignatura.disponible_periodo(periodo_matricular)
                    puedetomar = inscripcion.puede_tomar_materia(materia.asignatura)
                    estado = inscripcion.estado_asignatura(materia.asignatura)
                    totalmatriculaasignatura = inscripcion.total_matricula_asignatura(materia.asignatura)
                    data['PUEDE_MATRICULARSE_OTRA_VEZ'] = PUEDE_MATRICULARSE_OTRA_VEZ = variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ')
                    data['utiliza_gratuidades'] = UTILIZA_GRATUIDADES
                    data['porciento_perdida_parcial_gratuidad'] = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                    data['porciento_perdida_total_gratuidad'] = PORCIENTO_PERDIDA_TOTAL_GRATUIDAD

                    if programada and nivel:
                        if puedetomar:
                            if estado != 1:
                                if totalmatriculaasignatura > 1 and not PUEDE_MATRICULARSE_OTRA_VEZ:
                                    message = 'Aún no esta habilitada la matriculación por más de una vez en las materia'
                                    raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante; {message}")
                                else:
                                    data['id'] = inscripcion.id
                                    data['ida'] = materia.asignatura.id
                                    data['idam'] = materia.id
                                    data['nivel'] = nivel.id

                                    eParalelo = None
                                    if eMatricula:
                                        materias_asignadas = eMatricula.materiaasignada_set.values_list('materia__paralelo', flat=True).filter(status=True)
                                        if materias_asignadas:
                                            eParalelo = materias_asignadas[0]

                                    eMaterias_abiertas = materias_abiertas_salud(inscripcion.id, materia.asignatura.id, materia.id, nivel.id, eParalelo, True)


                                    if eMaterias_abiertas and eMaterias_abiertas['result'] == 'ok':
                                        data['eMaterias_abiertas'] = eMaterias_abiertas
                                    else:
                                        raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, proceso de matriculación no se encuentra activo. {eMaterias_abiertas['error']}")
                        else:
                            if estado != 1:
                                if materia.asignaturamalla.cantidad_predecesoras:
                                    listado_precedencia = ''
                                    for i, precedencia in enumerate(materia.asignaturamalla.lista_predecesoras()):
                                        listado_precedencia += precedencia.predecesora.asignatura.nombre
                                        if i < len(materia.lista_predecesoras) - 1:
                                            listado_precedencia += ","
                                    raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, La asignatura tiene precedencias: {listado_precedencia}")
                    else:
                        raise NameError(f"Estimad{'a' if persona.es_mujer() else 'o'} estudiante, proceso de matriculación no se encuentra activo")

                    template = get_template("alu_practicassalud/modal/inscribirpracticappasignatura.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': f'{ex}. Intente nuevamente más tarde.'})

            elif action == 'listadobitacorapracticas':
                try:
                    data['title'] = 'Bitácora de actividades'
                    listadomeses = []
                    dias_plazo_llenar_bitacora = 3
                    data['detallepreinsc'] = detallepreinsc = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt_alu(request.GET['id_practica'])), status=True)

                    data['title2'] = u'%s %s %s %s' % ((detallepreinsc.institucion.__str__() + (' - ').__str__() if detallepreinsc.institucion else ''),
                                    (detallepreinsc.itinerariomalla.__str__() + (' - ').__str__() if detallepreinsc.itinerariomalla else ''),
                                    (detallepreinsc.empresaempleadora.__str__() + (' - ').__str__() if detallepreinsc.empresaempleadora else ''),
                                    (detallepreinsc.otraempresaempleadora.__str__() if detallepreinsc.otraempresaempleadora else ''))

                    registrobitacoras = detallepreinsc.bitacoraactividadestudianteppp_set.filter(status=True).order_by('fechaini').annotate(fechamaxima=ExpressionWrapper(F('fechafin') + timedelta(days=dias_plazo_llenar_bitacora), output_field=DateTimeField()))
                    # data['evidenciaactividaddetalle'] = registrobitacoras.filter(fechamaxima__gte=datetime.now()) #para conocer cuales ya pasaron su fecha maxima
                    fechas_mensuales = list(rrule(MONTHLY, dtstart=detallepreinsc.fechadesde, until=detallepreinsc.fechahasta))
                    fechaactual = datetime.now().date()

                    for fecha in fechas_mensuales:
                        ultimo_dia = fecha.replace(day=calendar.monthrange(fecha.year, fecha.month)[1])
                        primer_dia = fecha.replace(day=1)
                        numeromes = fecha.month
                        anio = fecha.year
                        nomostrar = 0
                        for bita in registrobitacoras:
                            if bita.fechaini.month == fecha.month:
                                nomostrar = 1
                        if nomostrar == 0:
                            if fechaactual >= primer_dia.date():
                                if ultimo_dia.date():
                                    listadomeses.append([primer_dia, anio, '01', str(numeromes), str(ultimo_dia.day), ultimo_dia.date() + timedelta(days=dias_plazo_llenar_bitacora)])

                    data['fechaactual'] = fechaactual
                    data['listadomeses'] = listadomeses
                    data['periodo'] = periodo
                    # data['bitacoras'] = registrobitacoras.filter(fechamaxima__lte=datetime.now())
                    data['bitacoras'] = registrobitacoras
                    return render(request, "alu_practicassalud/listadobitacorappp.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/alu_practicaspro?info={}'.format(ex))

            elif action == 'detallebitacora':
                try:
                    data['title'] = u'Listado actividades bitacora'

                    dias_plazo_llenar_bitacora = 3
                    valida_registro_tardio_bitacora, now = False, datetime.now().date()
                    puede_modificar_bitacora, puede_enviar_a_revision = True, True

                    if 'idbitacora' in request.GET:
                        mesbitacora = BitacoraActividadEstudiantePpp.objects.get(pk=int(encrypt(request.GET['idbitacora'])))
                        data['pppinscripcion'] = pppinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=mesbitacora.practicasppinscripcion.id, status=True)
                        # if variable_valor('VALIDA_REGISTRO_BITACORA_PPPIR'):
                        mes = mesbitacora.fechafin.month
                        fecha = date(now.year, mes, calendar.monthrange(now.year, mes)[1]) + timedelta(days=dias_plazo_llenar_bitacora)
                        puede_modificar_bitacora = now <= fecha
                    else:
                        fechainicio = datetime.strptime(request.GET['fechaini'], '%Y-%m-%d').date()
                        fechafinal = datetime.strptime(request.GET['fechafin'], '%Y-%m-%d').date()
                        nombrebitacora = request.GET['nombrebitacora']
                        data['pppinscripcion'] = pppinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                        if bitacora := pppinscripcion.bitacoraactividadestudianteppp_set.filter(fechaini=fechainicio, fechafin=fechafinal, status=True).first():
                            mesbitacora = bitacora
                        else:
                            mesbitacora = BitacoraActividadEstudiantePpp(practicasppinscripcion=pppinscripcion,
                                                                         nombre='REGISTRO DE ACTIVIDADES DEL MES: ' + nombrebitacora,
                                                                         fechaini=fechainicio,
                                                                         fechafin=fechafinal)
                            mesbitacora.save(request)
                    data['subtitle'] = u'%s %s %s %s' % ((pppinscripcion.institucion.__str__() + (' - ').__str__() if pppinscripcion.institucion else ''),
                                                      (pppinscripcion.itinerariomalla.__str__() + (' - ').__str__() if pppinscripcion.itinerariomalla else ''),
                                                      (pppinscripcion.empresaempleadora.__str__() if pppinscripcion.empresaempleadora else ''),
                                                      ((' - ').__str__() + pppinscripcion.otraempresaempleadora.__str__() if pppinscripcion.otraempresaempleadora else ''))
                    data['mesbitacora'] = mesbitacora

                    data['listadodetalle'] = listadodetalle = mesbitacora.detallebitacoraestudianteppp_set.filter(status=True).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')
                    habilitaplan = False
                    carrera = pppinscripcion.inscripcion.carrera
                    if carrera.id in [112]:
                        habilitaplan = True
                    elif carrera.id in [1, 110]:
                        habilitaplan = True
                    data['habilitaplan'] = habilitaplan
                    # if mesbitacora.criterio.criteriodocenciaperiodo:
                    #     claseactividad = ClaseActividad.objects.filter(detalledistributivo__criteriodocenciaperiodo=mesbitacora.criterio.criteriodocenciaperiodo, detalledistributivo__distributivo__profesor=profesor, status=True).order_by('inicio', 'dia', 'turno__comienza')
                    #
                    # if mesbitacora.criterio.criterioinvestigacionperiodo:
                    #     claseactividad = ClaseActividad.objects.filter(detalledistributivo__criterioinvestigacionperiodo=mesbitacora.criterio.criterioinvestigacionperiodo, detalledistributivo__distributivo__profesor=profesor, status=True).order_by('inicio', 'dia', 'turno__comienza')
                    #
                    # if mesbitacora.criterio.criteriogestionperiodo:
                    #     claseactividad = ClaseActividad.objects.filter(detalledistributivo__criteriogestionperiodo=mesbitacora.criterio.criteriogestionperiodo, detalledistributivo__distributivo__profesor=profesor, status=True).order_by('inicio', 'dia', 'turno__comienza')
                    #
                    # diasclas = claseactividad.values_list('dia', 'turno_id')
                    # dt = mesbitacora.fechaini
                    # end = mesbitacora.fechafin
                    # step = timedelta(days=1)

                    # result = []
                    # while dt <= end:
                    #     dias_nolaborables = periodo.dias_nolaborables(dt)
                    #     if not dias_nolaborables:
                    #         for dclase in diasclas:
                    #             if dt.isocalendar()[2] == dclase[0]:
                    #                 result.append(dt.strftime('%Y-%m-%d'))
                    #     dt += step
                    #
                    # data['totalhorasplanificadas'] = totalhorasplanificadas = len(result)
                    # totalhorasregistradas, totalhorasaprobadas, porcentaje_cumplimiento = 0, 0, 0
                    #
                    # if th := listadodetalle.filter(status=True).aggregate(total=Sum('diferencia'))['total']:
                    #     horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                    #     totalhorasregistradas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))
                    #
                    # if th := listadodetalle.filter(estadoaprobacion=2, status=True).aggregate(total=Sum('diferencia'))['total']:
                    #     horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                    #     totalhorasaprobadas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))
                    #
                    # data['totalhorasregistradas'] = totalhorasregistradas
                    # data['totalhorasaprobadas'] = totalhorasaprobadas

                    # if totalhorasplanificadas:
                    #     if mesbitacora.estadorevision == 3:
                    #         porcentaje_cumplimiento = 100 if totalhorasaprobadas > totalhorasplanificadas else round((totalhorasaprobadas / totalhorasplanificadas) * 100, 2)
                    #     else:
                    #         porcentaje_cumplimiento = 100 if totalhorasregistradas > totalhorasplanificadas else round((totalhorasregistradas / totalhorasplanificadas) * 100, 2)

                    # if mesbitacora.criterio.criteriodocenciaperiodo:
                    #     puede_enviar_a_revision = not mesbitacora.criterio.criteriodocenciaperiodo.criterio.pk == 167

                    # data['porcentaje_cumplimiento'] = porcentaje_cumplimiento
                    data['valida_registro_tardio_bitacora'] = valida_registro_tardio_bitacora
                    data['puede_modificar_bitacora'] = puede_modificar_bitacora and mesbitacora.estadorevision == 1
                    data['puede_enviar_a_revision'] = puede_enviar_a_revision
                    return render(request, "alu_practicassalud/detallebitacorappp.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "aData": {}, "message": '{} - Error on line {}'.format(str(ex), sys.exc_info()[-1].tb_lineno)})

            elif action == 'buscarpersonas':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filter = Q(administrativo__isnull=False, status=True)
                    if len(s) == 1: filter &= Q(Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q))
                    if len(s) == 2: filter &= Q(Q(Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) | (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1])))
                    if len(s) >  2: filter &= Q((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2])))

                    return JsonResponse({"result": "ok", "results": [{"id": x.id, "name": "{}".format(x.nombre_completo())} for x in Persona.objects.filter(filter).order_by('apellido1')[:15]]})
                except Exception as ex:
                    pass

            elif action == 'addbitacorappp':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar bitácora'
                    mesbitacora = BitacoraActividadEstudiantePpp.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = BitacoraActividadPppForm(initial={'fecha': mesbitacora.fechaini.date()})
                    # form.fields['persona'].queryset = Persona.objects.none()
                    inscripcion = Inscripcion.objects.get(pk=int(request.GET['insc']))
                    if inscripcion:
                        form.iniciar(inscripcion.carrera)
                    data['mesbitacora'] = mesbitacora
                    data['form'] = form
                    data['mBitacora'] = "%02d" % mesbitacora.fechaini.month
                    template = get_template("alu_practicassalud/modal/formbitacora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editbitacorappp':
                try:
                    data['title'] = u'Editar bitácora'
                    data['action'] = request.GET['action']
                    data['detallebitacora'] = detallebitacora = DetalleBitacoraEstudiantePpp.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    form = BitacoraActividadPppForm(initial={'titulo': detallebitacora.titulo,
                                                          'fecha': detallebitacora.fecha.date(),
                                                          'hora': detallebitacora.horainicio,
                                                          'horafin': detallebitacora.horafin,
                                                          'descripcion': detallebitacora.descripcion,
                                                          'link': detallebitacora.link })
                    form.iniciar(detallebitacora.bitacorapractica.practicasppinscripcion.inscripcion.carrera, detallebitacora)
                    data['form'] = form
                    template = get_template("alu_practicassalud/modal/formbitacora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'detalleregistrobitacora':
                try:
                    data = {}
                    data['detalle'] = detalle = DetalleBitacoraEstudiantePpp.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("alu_practicassalud/modal/detalleregistrobitacorappp.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'generarbitacorapdf':
                try:
                    data_extra, valida_estado_2 = {}, True
                    bitacora = BitacoraActividadEstudiantePpp.objects.filter(id=int(request.GET.get('id', 0)), status=True).first()
                    detallebitacora = DetalleBitacoraEstudiantePpp.objects.filter(bitacorapractica=bitacora, status=True).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')
                    # claseactividad = ClaseActividad.objects.filter(detalledistributivo=bitacora.criterio, detalledistributivo__distributivo__profesor=bitacora.criterio.distributivo.profesor, status=True).values_list('dia', 'turno_id').order_by('inicio', 'dia', 'turno__comienza')
                    dt, end = bitacora.fechaini, bitacora.fechafin
                    result = []
                    # while dt <= end:
                    #     dias_nolaborables = periodo.dias_nolaborables(dt)
                    #     # if not dias_nolaborables:
                    #     #     for dclase in claseactividad:
                    #     #         if dt.isocalendar()[2] == dclase[0]:
                    #     #             result.append(dt.strftime('%Y-%m-%d'))
                    #     dt += timedelta(days=1)

                    # data_extra['totalhorasplanificadas'] = totalhorasplanificadas = result.__len__()
                    totalhorasregistradas, porcentaje_cumplimiento = 0, 0

                    if th := detallebitacora.filter(status=True).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                        totalhorasregistradas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    # if th := detallebitacora.filter(estadoaprobacion=2, status=True).aggregate(total=Sum('diferencia'))['total']:
                    #     horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                    #     totalhorasaprobadas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    # if bitacora.criterio.criteriodocenciaperiodo:
                    #     if valida_estado_2 := not bitacora.criterio.criteriodocenciaperiodo.criterio.pk == 167:
                    #         porcentaje_cumplimiento = (100 if totalhorasaprobadas > totalhorasplanificadas else ((totalhorasaprobadas/totalhorasplanificadas) * 100)) if totalhorasplanificadas else 0
                    # else:
                    #     porcentaje_cumplimiento = (100 if totalhorasregistradas > totalhorasplanificadas else ((totalhorasregistradas/totalhorasplanificadas) * 100)) if totalhorasplanificadas else 0

                    data_extra['DEBUG'] = DEBUG
                    data_extra['persona'] = persona
                    data_extra['bitacora'] = bitacora
                    data_extra['valida_estado_2'] = valida_estado_2
                    data_extra['detallebitacora'] = detallebitacora
                    data_extra['fecha_creacion'] = datetime.now().date()
                    # data_extra['totalhorasaprobadas'] = totalhorasaprobadas
                    data_extra['totalhorasregistradas'] = totalhorasregistradas
                    # data_extra['porcentaje_cumplimiento'] = porcentaje_cumplimiento

                    return conviert_html_to_pdf_name('../templates/alu_practicassaludinscripcion/informe_bitacora_actividad_ppp.html', data_extra, f"bitacora_{persona.usuario.username}_{bitacora.pk}.pdf")
                except Exception as ex:
                    pass

            elif action == 'actualizardatossalud':
                try:
                    search, url_vars, numerofilas, tab = request.GET.get('s', ''), '', 15, request.GET.get('tab', '')
                    listadoresultado = []
                    filters = Q(status=True)
                    data['tab'] = tab
                    data['title'] = u'Actualización de datos personales '
                    if not inscripcion:
                        inscripcion = Inscripcion.objects.get(pk=int(encrypt(request.GET['idalu'])))
                    data['inscripcion'] = inscripcion
                    data['listado'] = listadoresultado
                    return render(request, 'alu_practicassaludinscripcion/viewdatossalud.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(request.path + f'?info={ex=}')

            elif action == 'detalledatos':
                try:
                    data['puede_modificar_hv'] = variable_valor('PUEDE_MODIFICAR_HV')
                    data['title'] = request.GET.get('title', 'Listado de resultados')
                    data['subtitle'] = request.GET.get('subtitle', 'Estudiantes inscritos en prácticas pre profesionales')
                    data['hoy'] = hoy
                    data['identificador'] = identificador = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = int(request.GET.get('idins', 0))
                    listado = []
                    listadoaux = []
                    resultados = []
                    bandera, idextra, fecha, estado, documento = 0, 0, '', 'PENDIENTE', ''
                    filters = Q(status=True)
                    if not inscripcion:
                        inscripcion = Inscripcion.objects.get(pk=idins)
                    if not persona:
                        data['persona'] = persona = Persona.objects.get(id=inscripcion.persona.id)
                    if identificador > 0 and identificador == 1: #discapacidad del estudiante > 30%
                        data['perfil'] = perfil = persona.mi_perfil()
                        if perfil.archivo: #Migra el registro de carnet al campo de salud
                            if not PerfilInscripcionExtensionSalud.objects.filter(status=True, perfilinscripcion=perfil).exists():
                                pdiscapacidad = PerfilInscripcionExtensionSalud(perfilinscripcion=perfil, fecha=hoy, archivodiscapacidad=perfil.archivo)
                                pdiscapacidad.save()
                        data['documentopersonal'] = persona.documentos_personales()

                    if identificador > 0 and identificador == 2: #Enfermedades catastróficas del estudiante
                        data['enfermedades'] = enfermedades = persona.mis_enfermedades().order_by('-id')

                    if identificador > 0 and identificador == 3: # Familiar Discapacidad
                        data['familiares'] = familiares = persona.familiares().order_by('-id')

                    if identificador > 0 and identificador == 4: #embarazo de la estudiante
                        data['embarazos'] = embarazos = persona.personadetallematernidad_set.filter(status=True).order_by('-pk')

                    if identificador > 0 and identificador == 5: #requisitos de la estudiante
                        perfil = persona.mi_perfil()
                        data['requisito'] = requisito = RequisitoPracticappSalud.objects.filter(status=True, persona=persona).first()

                    data['listado'] = resultados
                    template = get_template('alu_practicassaludinscripcion/detalledatosestudiante.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': 'Problemas al obtener los datos, intente más tarde por favor.'})

            elif action == 'actualizarrequisito':
                try:
                    data['title'] = u'Requisitos'
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    form = RequisitoPPPSaludForm()
                    tienearchivo = False
                    if requisito := RequisitoPracticappSalud.objects.filter(status=True, persona=persona).first():
                        form.fields['observacion'].initial = requisito.observacion
                        if requisito.archivo:
                            form.fields['archivo'].initial = requisito.archivo
                            tienearchivo = True
                    data['form'] = form
                    data['tienearchivo'] = tienearchivo
                    template = get_template('alu_practicassaludinscripcion/modal/ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editdiscapacidad':
                try:
                    from sga.models import Discapacidad
                    data['title'] = u'Discapacidad'
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    perfil = persona.mi_perfil()
                    form = DiscapacidadSaludForm(initial=model_to_dict(perfil))
                    tienearchivo = True if perfil.archivo else False
                    if pdiscapacidad := PerfilInscripcionExtensionSalud.objects.filter(status=True, perfilinscripcion=perfil).first():
                        if pdiscapacidad.archivodiscapacidad:
                            form.fields['archivocarnet'].initial = pdiscapacidad.archivodiscapacidad
                    data['form'] = form
                    data['tienearchivo'] = tienearchivo
                    data['switchery'] = True
                    data['tipodis'] = Discapacidad.objects.filter(status=True)
                    template = get_template('alu_practicassaludinscripcion/modal/formdiscapacidadsalud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addenfermedad':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    form = PersonaEnfermedadSaludForm()
                    data['form'] = form
                    template = get_template('alu_practicassaludinscripcion/modal/ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editenfermedad':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    data['enfermedad'] = enfermedad = PersonaEnfermedad.objects.get(id=int(encrypt(request.GET['id'])))
                    data['id'] = enfermedad.id
                    form = PersonaEnfermedadSaludForm(initial=model_to_dict(enfermedad))
                    if penfermedad := PersonaEnfermedadExtensionSalud.objects.filter(status=True, personaenfermedad=enfermedad).first():
                        if penfermedad.archivoenfermedad:
                            form.fields['archivoenfermedad'].initial = penfermedad.archivoenfermedad
                    data['form'] = form
                    template = get_template('alu_practicassaludinscripcion/modal/ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addembarazo':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    form = PersonaDetalleMaternidadSaludForm()
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('alu_practicassaludinscripcion/modal/formembarazosalud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editembarazo':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    data['id'] = id = request.GET['id']
                    embarazo = PersonaDetalleMaternidad.objects.get(id=id)
                    form = PersonaDetalleMaternidadSaludForm(initial=model_to_dict(embarazo))
                    if pembarazo := PersonaDetalleMaternidadExtensionSalud.objects.filter(status=True, personamaternidad=embarazo).first():
                        if pembarazo.archivoembarazo:
                            form.fields['archivo'].initial = pembarazo.archivoembarazo
                            data['banderaarchivo'] = True
                        else:
                            form.fields['archivo'].required = True
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('alu_practicassaludinscripcion/modal/formembarazosalud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'consultacedula':
                try:
                    cedula = request.GET['cedula'].strip().upper()
                    id=request.GET.get('id', 0)
                    datospersona = Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS'+cedula)) | Q(cedula=cedula[2:]), status=True).first()
                    if datospersona:
                        if datospersona == persona:
                            return JsonResponse({"result": "bad", 'mensaje': 'No puede agregar su propia cédula.'})
                        if persona.personadatosfamiliares_set.filter(identificacion=cedula, status=True).exclude(id=id).exists():
                            return JsonResponse({"result": "bad", 'mensaje':'Identificación ingresada ya se encuentra registrada en un familiar'})
                        perfil_i = datospersona.perfilinscripcion_set.filter(status=True).first()
                        editdiscapacidad=False
                        if len(datospersona.mis_perfilesusuarios()) == 1 and datospersona.tiene_usuario_externo():
                            editdiscapacidad = True
                        elif perfil_i and not perfil_i.estadoarchivodiscapacidad == 2:
                            editdiscapacidad = True
                        context = {}
                        if perfil_i and perfil_i.tienediscapacidad:
                            context = {'tipodiscapacidad': perfil_i.tipodiscapacidad.id if perfil_i.tipodiscapacidad else False,
                                        'tienediscapacidad': perfil_i.tienediscapacidad,
                                        'porcientodiscapacidad': perfil_i.porcientodiscapacidad,
                                        'carnetdiscapacidad': perfil_i.carnetdiscapacidad,
                                        'institucionvalida': perfil_i.institucionvalida.id if perfil_i.institucionvalida else False,
                                        'ceduladiscapacidad': perfil_i.archivo.url if perfil_i.archivo else False ,
                                        'archivoautorizado': perfil_i.archivovaloracion.url if perfil_i.archivovaloracion else False,
                                        }
                        return JsonResponse({"result": "ok",
                                             "apellido1": datospersona.apellido1,
                                             "apellido2": datospersona.apellido2,
                                             "nacimiento": datospersona.nacimiento.strftime('%Y-%m-%d'),
                                             "nombres": datospersona.nombres,
                                             "telefono": datospersona.telefono,
                                             "telefono_conv": datospersona.telefono_conv,
                                             "sexo": datospersona.sexo.id if datospersona.sexo else '' ,
                                             "puedeeditar": editdiscapacidad,
                                             "perfil_i": context})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": str(ex)})

            elif action == 'addfamiliar':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    form = FamiliarSaludForm()
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Informació Básica', visible_fields[:19]),
                             (2, 'Información Laboral', visible_fields[19:27]),
                             (3, 'Discapacidad', visible_fields[27:total_fields])
                            ]
                    data['form'] = lista
                    data['switchery']=True
                    template = get_template('alu_practicassaludinscripcion/modal/formfamiliarsalud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editfamiliar':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    data['title'] = u'Editar familiar'
                    data['id'] = id = encrypt(request.GET['id'])
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(id))
                    apellido1, apellido2, nombres, editdiscapacidad, sexo = '', '', familiar.nombre, False, None
                    if familiar.personafamiliar:
                        apellido1 = familiar.personafamiliar.apellido1
                        apellido2 = familiar.personafamiliar.apellido2
                        nombres = familiar.personafamiliar.nombres
                        sexo = familiar.personafamiliar.sexo
                        perfil_f = familiar.personafamiliar.perfilinscripcion_set.filter(status=True).first()
                        estado = True if perfil_f and perfil_f.estadoarchivodiscapacidad == 2 else False
                        if len(familiar.personafamiliar.mis_perfilesusuarios()) == 1 and familiar.personafamiliar.tiene_usuario_externo():
                            editdiscapacidad = True
                        elif not estado:
                            editdiscapacidad = True
                    else:
                        editdiscapacidad = True
                    banderacedula = 0
                    if familiar.cedulaidentidad:
                        banderacedula = 1
                    data['banderacedula'] = banderacedula
                    data['edit_d'] = editdiscapacidad
                    form = FamiliarSaludForm(initial={'identificacion': familiar.identificacion,
                                                 'parentesco': familiar.parentesco,
                                                 'nombre': nombres,
                                                 'apellido1': apellido1,
                                                 'apellido2': apellido2,
                                                 'sexo': sexo,
                                                 'nacimiento': familiar.nacimiento,
                                                 'fallecido': familiar.fallecido,
                                                 'tienediscapacidad': familiar.tienediscapacidad,
                                                 'telefono': familiar.telefono,
                                                 'niveltitulacion': familiar.niveltitulacion,
                                                 'ingresomensual': familiar.ingresomensual,
                                                 'formatrabajo': familiar.formatrabajo,
                                                 'telefono_conv': familiar.telefono_conv,
                                                 'trabajo': familiar.trabajo,
                                                 'convive': familiar.convive,
                                                 'sustentohogar': familiar.sustentohogar,
                                                 'essustituto': familiar.essustituto,
                                                 'autorizadoministerio': familiar.autorizadoministerio,
                                                 'tipodiscapacidad': familiar.tipodiscapacidad,
                                                 'porcientodiscapacidad': familiar.porcientodiscapacidad,
                                                 'carnetdiscapacidad': familiar.carnetdiscapacidad,
                                                 'institucionvalida': familiar.institucionvalida,
                                                 'tipoinstitucionlaboral': familiar.tipoinstitucionlaboral,
                                                 'tienenegocio': familiar.tienenegocio,
                                                 'esservidorpublico': familiar.esservidorpublico,
                                                 'bajocustodia': familiar.bajocustodia,
                                                 'tienenegocio': familiar.tienenegocio,
                                                 'cedulaidentidad': familiar.cedulaidentidad,
                                                 'ceduladiscapacidad': familiar.ceduladiscapacidad,
                                                 'archivoautorizado': familiar.archivoautorizado,
                                                 'cartaconsentimiento': familiar.cartaconsentimiento,
                                                 'archivocustodia': familiar.archivocustodia,
                                                 'centrocuidado': familiar.centrocuidado,
                                                 'centrocuidadodesc': familiar.centrocuidadodesc,
                                                 'negocio': familiar.negocio, })
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Informació Básica', visible_fields[:19]),
                             (2, 'Información Laboral', visible_fields[19:27]),
                             (3, 'Discapacidad', visible_fields[27:total_fields])
                             ]
                    form.edit()
                    data['form'] = lista
                    data['switchery'] = True
                    template = get_template('alu_practicassaludinscripcion/modal/formfamiliarsalud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addfamiliarenfermedad':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    data['id'] = id = encrypt(request.GET['id'])
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(id))
                    form = FamiliarEnfermedadSaludForm(initial={'essustituto': familiar.essustituto, 'archivoautorizado': familiar.archivoautorizado})
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('alu_practicassaludinscripcion/modal/formenfermedadfamiliarsalud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editfamiliarenfermedad':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    data['enfermedad'] = enfermedad = EnfermedadFamiliarSalud.objects.get(id=int(encrypt(request.GET['id'])))
                    data['id'] = enfermedad.id
                    data['familiar'] = familiar = enfermedad.personafamiliarext.personafamiliar
                    form = FamiliarEnfermedadSaludForm(initial={'essustituto': familiar.essustituto, 'archivoautorizado': familiar.archivoautorizado,
                                                                'enfermedad':enfermedad.enfermedad, 'archivoenfermedad': enfermedad.archivoenfermedad})
                    if not enfermedad.archivoenfermedad:
                        form.fields['archivoenfermedad'].required = True
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('alu_practicassaludinscripcion/modal/formenfermedadfamiliarsalud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'actualizarfamiliarninio':
                try:
                    data['tab'] = tab = int(request.GET.get('identificador', 0))
                    data['idins'] = idins = request.GET['idins']
                    data['id'] = id = encrypt(request.GET['id'])
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(id))
                    form = FamiliarNinioSaludForm(initial={'bajocustodia': familiar.bajocustodia,
                                                           'parentesco': familiar.parentesco,
                                                           'cedulaidentidad': familiar.cedulaidentidad,
                                                           'archivocustodia': familiar.archivocustodia})
                    # form.edit(familiar)
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('alu_practicassaludinscripcion/modal/formniniofamiliarsalud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'obtenerlistamaterias':
                try:
                    idinscripcion = request.GET['idinscripcion']
                    idpreins = request.GET['idpreins']
                    idnivel = request.GET['idnivel']
                    idmateria = request.GET['idmateria']
                    paralelo = request.GET['paralelo']

                    detalle = DetallePreInscripcionPracticasPP.objects.get(pk=idpreins)
                    materiaseleccionada = Materia.objects.get(pk=idmateria)
                    eAsignaturas = ItinerarioAsignaturaSalud.objects.filter(itinerariomalla=detalle.itinerariomalla, status=True).exclude(asignaturamalla__asignatura=materiaseleccionada.asignatura)
                    eListadoAsignaturas = eAsignaturas
                    if habilita_inscripcion_nivel:
                        if detalle2 := detalle.inscripcion.detallepreinscripcionpracticaspp_set.filter(status=True, preinscripcion=detalle.preinscripcion, itinerariomalla__nivel=detalle.itinerariomalla.nivel).exclude(itinerariomalla=detalle.itinerariomalla).first():
                            if eAsignaturas2 := ItinerarioAsignaturaSalud.objects.filter(itinerariomalla=detalle2.itinerariomalla, status=True):
                                eListadoAsignaturas = eAsignaturas | eAsignaturas2
                    listado_materias = [int(idmateria)]
                    for a in eListadoAsignaturas:
                        eMaterias_abiertas = materias_abiertas_salud(idinscripcion, a.asignaturamalla.asignatura.id, a.asignaturamalla.id, idnivel, paralelo, True)
                        if len(eMaterias_abiertas['materias']) > 0:
                            listado_materias.append(list(eMaterias_abiertas['materias'])[0])
                    return JsonResponse({"result": True, "listado": listado_materias})
                except Exception as ex:
                    return JsonResponse({"result": False})

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Inscripcion de prácticas preprofesionales Salud'
                data['idalu'] = inscripcion.id
                data['inscripcion'] = inscripcion
                itinerarios = []

                if not inscripcion.inscripcionmalla_set.values('id').exists():
                    return HttpResponseRedirect("/?info=Debe tener malla asociada para poder inscribirse.")
                if inscripcion.mi_malla():
                    if inscripcion.mi_malla().itinerariosmalla_set.filter(status=True).exists():
                        listaitinerariorealizado = inscripcion.cumple_total_horas_itinerario()
                        itinerariosvalidosid = []
                        for it in inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True):
                            nivelhasta = it.nivel.orden
                            if inscripcion.todas_materias_aprobadas_rango_nivel(1, nivelhasta - 1):
                                itinerariosvalidosid.append(it.pk)
                        itinerarios = inscripcion.mi_malla().itinerariosmalla_set.filter(status=True, nivel__orden__lte=inscripcion.mi_nivel().nivel.orden + 1).filter(pk__in=itinerariosvalidosid)
                data['itinerarios'] = itinerarios

                prinscripcion = PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date(), coordinacion__in=[1])
                data['inglesaprobado'] = haber_aprobado_modulos_ingles(inscripcion.id)
                data['computacionaprobado'] = haber_aprobado_modulos_computacion(inscripcion.id)

                detalle = DetallePreInscripcionPracticasPP.objects.filter(status=True, inscripcion=inscripcion, itinerariomalla__in=itinerarios)
                preinsestudiante = detalle.values_list('preinscripcion_id', flat=True)
                convocatorias_habilitadas = list(ExtPreInscripcionPracticasPP.objects.values_list('preinscripcion_id', flat=True).filter(status=True, preinscripcion_id__in=preinsestudiante, finicioconvocatoria__lte=hoy, ffinconvocatoria__gte=hoy))
                data['listadopreinscrip'] = lisresp = PreInscripcionPracticasPP.objects.filter(id__in=convocatorias_habilitadas)

                totalofertas = 0
                for d in lisresp:
                    totalofertas += d.configuracioninscripcionpracticaspp_set.filter(status=True, estado=2, fechainiciooferta__lte=hoy, fechafinoferta__gte=hoy).count()
                data['totalofertas'] = totalofertas

                data['puede_preinscribirseppp'] = x = inscripcion.puede_preinscribirseppp()
                fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()
                excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
                data['esexonerado'] = fechainicioprimernivel <= excluiralumnos
                data['lista_estados'] = [1, 2]

                return render(request, "alu_practicassaludinscripcion/view.html", data)
            except Exception as ex:
                return redirect('/?info={}'.format(ex))


def valida_turno_seleccion(persona, idoferta, idpreinsc):
    try:
        genero = 'a' if persona.es_mujer() else 'o'
        oferta = ConfiguracionInscripcionPracticasPP.objects.get(pk=idoferta)
        detallepreinscripcion = DetallePreInscripcionPracticasPP.objects.get(pk=idpreinsc)
        grupoorden = detallepreinscripcion.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if detallepreinscripcion.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
        if not oferta.cantidad_inscritos_oferta() < oferta.cupo:
            return {"result": False, 'sincupo': True, 'message': f'Estimad{genero} estudiante, ya no existe cupos disponibles en este momento.'}
        if not grupoorden:
            return {"result": False, 'message': f'Estimad{genero} estudiante, no existe asignado un ORDEN DE SELECCIÓN en la convocatoria de prácticas pre profesionales.'}
        if not variable_valor('VALIDA_SELECCION_TURNO'):
            return {"result": True}
        if orden := detallepreinscripcion.inscripcion.ordenprioridadinscripcion_set.first():
            turnoestudiante = orden.obtenerturnoinscripcion(grupoorden, detallepreinscripcion.preinscripcion)
            if not turnoestudiante:
                return {"result": False, 'message': f'Estimad{genero} estudiante, usted NO cuenta con un TURNO para la selección en la convocatoria de prácticas pre profesionales.'}
            else:
                if turnoestudiante.orden > 1:
                    numero = turnoestudiante.orden - 1
                    limite = 0  # El limite de consultas de selecciones anteriores hasta 20 antes del estudiante y los 20 primeros
                    while numero >= 1:
                        if limite == 20: numero = 20
                        itinerario_oferta = oferta.itinerariomalla.values_list('id', flat=True).all()
                        turnoanterior = orden.seleccionturnoanterior(grupoorden, turnoestudiante.configuracionorden, numero, itinerario_oferta)
                        if turnoanterior and turnoanterior.activo:  # si esta activo el turno, se consulta si ese turno ya realizo la seleccion
                            if not turnoanterior.historialinscricionoferta_set.filter(status=True, practicasppinscripcion__itinerariomalla_id__in=itinerario_oferta).order_by('fecha').last():
                                return {"result": False, 'message': f'Estimad{genero} estudiante, por favor ESPERAR a que el turno anterior({turnoanterior.inscripcion.persona}) seleccione su plaza. Después de ello, usted podrá continuar con su selección.'}
                        numero -= 1
                        limite += 1
        return {"result": True}
    except Exception as ex:
        return {"result": False, 'message': 'Problemas al validar el turno, intente nuevamente más tarde.'}