from django.contrib.auth.decorators import login_required
from decorators import secure_module, last_access
from django.db import transaction
from sga.commonviews import adduserdata
from datetime import datetime, timedelta
from ejecuform.models import EventoFormacionEjecutiva, ConvocatoriaFormacionEjecutiva, InscripcionFormacionEjecutiva, \
    CategoriaEventoFormacionEjecutiva, DetalleAsignaturasFormacionEjecutiva, ObjetivoEventoFormacionEjecutiva, \
    InstructorFormacionEjecutiva, ModeloEvaluativoGeneralFormacionEjecutiva, ModeloEvaluativoFormacionEjecutiva, \
    NotaFormacionEjecutiva
from posgrado.models import CohorteMaestria
from sga.models import Nivel, AsignaturaMalla, Materia, Persona, PerfilUsuario, Carrera, Malla, Profesor, ProfesorMateria
from django.db.models.query_utils import Q
from sga.funciones import MiPaginador, log, validarcedula, generar_nombre, calculate_username, generar_usuario_admision, \
    entero_a_romano, variable_valor, generar_usuario
from sagest.models import Rubro, TipoOtroRubro
from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from ejecuform.forms import EventoFormacionEjecutivaForm, DatosConvocatoriaForm, RegistroFormacionEjecutivaForm, DatosConvocatoriaRubroForm, \
    DatosConvocatoriaFechasForm, ModulosConvocatoriaForm, ModeloEvaluativoFormacionGeneralEjecutivaForm, ModeloEvaluativoFormacionEjecutivaForm
from django.template.loader import get_template
from sga.templatetags.sga_extras import encrypt
from django.contrib.auth.models import Group
import json
import os
import pyqrcode
from settings import SITE_STORAGE
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavevistaprevia_2
import time
@login_required(redirect_field_name='ret', login_url='/loginsga')
#@secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['personasesion'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    hoy = datetime.now().date()
    periodo = request.session['periodo']

    data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')
    # data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = 'http://127.0.0.1:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = 'https://sga.unemi.edu.ec' if not IS_DEBUG else 'http://127.0.0.1:8000'
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'cohortes':
            try:
                lista = []
                eCohortes = CohorteMaestria.objects.filter(status=True, periodoacademico__isnull=False, fecha_creacion__date__year__gte=2022).order_by('-periodoacademico__id').distinct()
                for eCohorte in eCohortes:
                    if eCohorte.periodoacademico.fin > datetime.now().date():
                        lista.append([eCohorte.id, f'{eCohorte.maestriaadmision.carrera} - {eCohorte.descripcion}'])
                        print(f'{eCohorte.maestriaadmision.carrera} - {eCohorte.descripcion}')
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'asignaturas':
            try:
                eCohorte = CohorteMaestria.objects.get(pk=request.POST['id'])
                eCarrera = eCohorte.maestriaadmision.carrera
                ePeriodo = eCohorte.periodoacademico
                idasi = []
                if Nivel.objects.filter(status=True, periodo=ePeriodo).exists():
                    eNivel = Nivel.objects.filter(status=True, periodo=ePeriodo).first()
                    eMaterias = Materia.objects.filter(status=True, nivel=eNivel).order_by('-id')
                    if eMaterias.exists():
                        for eMateria in eMaterias:
                            if eMateria.inicio < datetime.now().date():
                                idasi.append(eMateria.asignaturamalla.id)
                        eAsignaturas = AsignaturaMalla.objects.filter(status=True, malla__carrera=eCarrera).exclude(id__in=idasi)
                    else:
                        eAsignaturas = AsignaturaMalla.objects.filter(status=True, malla__carrera=eCarrera).order_by('id')
                else:
                    eAsignaturas = AsignaturaMalla.objects.filter(status=True, malla__carrera=eCarrera).order_by('id')
                lista = []
                for eAsignatura in eAsignaturas:
                    lista.append([eAsignatura.id, eAsignatura.asignatura.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addevento':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() in ['.jpg', '.png']:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .png"})

                f = EventoFormacionEjecutivaForm(request.POST, request.FILES)
                if f.is_valid():
                    if not EventoFormacionEjecutiva.objects.filter(status=True, nombre=f.cleaned_data['nombre']).exists():
                        if 'activo' in request.POST:
                            activo = True
                        else:
                            activo = False

                        if 'moodle' in request.POST:
                            moodle = True
                        else:
                            moodle = False

                        banner = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("formacionejecutiva_banner_", newfile._name)
                            banner = newfile

                        hora = f.cleaned_data['horas']
                        minutos = f.cleaned_data['minutos']

                        duracion = timedelta(hours=hora, minutes=minutos)
                        eEvento = EventoFormacionEjecutiva(nombre=f.cleaned_data['nombre'],
                                                           categoria=f.cleaned_data['categoria'],
                                                           nivel=f.cleaned_data['nivel'],
                                                           modalidad=f.cleaned_data['modalidad'],
                                                           descripcion=f.cleaned_data['corta'],
                                                           descripciondet=f.cleaned_data['descripcion'],
                                                           alias=f.cleaned_data['alias'],
                                                           banner=banner,
                                                           duracion=duracion,
                                                           activo=activo,
                                                           mooc=moodle)
                        eEvento.save(request)

                        if not 'lista_items1' in request.POST:
                            raise NameError('Debe adicionar un objetivo de aprendizaje')

                        for registro in json.loads(request.POST['lista_items1']):
                            eObjetivo = ObjetivoEventoFormacionEjecutiva(evento=eEvento,
                                                                         descripcion=registro['objetivo'])
                            eObjetivo.save(request)
                        log(u'Adicionó un evento de formación ejecutiva: %s' % eEvento, request, "add")
                        # return HttpResponseRedirect('/adm_formacionejecutiva')
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": True, "mensaje": f"Ya existe un evento registrado como {f.cleaned_data['nombre']}."}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'editevento':
            try:
                with transaction.atomic():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile.size > 10485760:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                        else:
                            newfiles = request.FILES['archivo']
                            newfilesd = newfiles._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext.lower() in ['.jpg', '.png']:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .png"})

                    eEvento = EventoFormacionEjecutiva.objects.get(pk=int(request.POST['id']))
                    f = EventoFormacionEjecutivaForm(request.POST, request.FILES)

                    if f.is_valid():
                        if not EventoFormacionEjecutiva.objects.filter(status=True, nombre=f.cleaned_data['nombre']).exclude(pk=eEvento.id).exists():
                            banner = None
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("formacionejecutiva_banner_", newfile._name)
                                banner = newfile

                            hora = f.cleaned_data['horas']
                            minutos = f.cleaned_data['minutos']

                            duracion = timedelta(hours=hora, minutes=minutos)

                            eEvento.nombre = f.cleaned_data['nombre']
                            eEvento.categoria = f.cleaned_data['categoria']
                            eEvento.modalidad = f.cleaned_data['modalidad']
                            eEvento.alias = f.cleaned_data['alias']
                            eEvento.duracion = duracion
                            eEvento.descripcion = f.cleaned_data['descripcion']
                            eEvento.nivel = f.cleaned_data['nivel']
                            if banner:
                                eEvento.banner = banner

                            if 'activo' in request.POST:
                                activo = True
                            else:
                                activo = False

                            eEvento.activo = activo
                            eEvento.save(request)
                            log(u'Actualizó evento de formación ejecutiva: %s' % eEvento, request, "edit")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({"result": True, "mensaje": f"Ya existe un evento registrado como {f.cleaned_data['nombre']}."}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'consultacedula':
            try:
                cedula = request.POST['cedula'].strip()
                hoy = datetime.now().date()
                resp = validarcedula(cedula)
                if resp != 'Ok':
                    return JsonResponse({"result": "bad", "mensaje": resp})

                datospersona = None
                provinciaid = 0
                cantonid = 0
                cantonnom = ''
                lugarestudio = ''
                carrera = ''
                profesion = ''
                institucionlabora = ''
                cargo = ''
                teleoficina = ''
                idgenero = 0
                habilitaemail = 0
                if cedula:
                    if Persona.objects.filter(status=True, cedula=cedula).exists():
                        datospersona = Persona.objects.filter(status=True, cedula=cedula).first()
                if datospersona:
                    return JsonResponse({"result": "ok", "idpersona": datospersona.id, "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                         "nombres": datospersona.nombres, "email": datospersona.email, "genero":datospersona.sexo.nombre, 'telefono': datospersona.telefono})
                else:
                    return JsonResponse({"result": "no"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'consultacedula2':
            try:
                cedula = request.POST['cedula'].strip()
                hoy = datetime.now().date()
                if request.POST['tipoidentificacion'].strip() == '1':
                    resp = validarcedula(cedula)
                    if resp != 'Ok':
                        raise NameError(u"%s."%(resp))

                nomevento = EventoFormacionEjecutiva.objects.filter(pk=request.POST['evento']).first()
                datospersona = None
                provinciaid = 0
                cantonid = 0
                cantonnom = ''
                lugarestudio = ''
                carrera = ''
                profesion = ''
                institucionlabora = ''
                cargo = ''
                teleoficina = ''
                idgenero = 0
                habilitaemail = 0
                if cedula:
                    if Persona.objects.filter(cedula=cedula).exists():
                        datospersona = Persona.objects.get(cedula=cedula)
                    elif Persona.objects.filter(pasaporte=cedula).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula)
                if datospersona:

                    postulante = datospersona
                    # valida ya está graduado en la maestria

                    # if Graduado.objects.filter(status=True, inscripcion__persona=postulante, inscripcion__carrera=nomcarrera).exists():
                    #     raise NameError("Usted ya se encuentra graduado en la maestría seleccionada")

                    if InscripcionFormacionEjecutiva.objects.filter(persona=postulante, convocatoria__evento=nomevento, activo=True, status=True).exists():
                        obtenerinscripcion = InscripcionFormacionEjecutiva.objects.filter(persona=postulante,
                                                          convocatoria__evento=nomevento,
                                                          activo=True, status=True)[0]
                        raise NameError(u"Usted ya se encuentra registrado, en la convocatoria %s. Un asesor/a lo contactará en el menor tiempo posible, revise su correo electrónico para más información." % (obtenerinscripcion.convocatoria))

                    return JsonResponse({"result": "ok", "idpersona": datospersona.id, "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                         "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "genero":datospersona.sexo.id,
                                         "direccion": datospersona.direccion})
                else:
                    return JsonResponse({"result": "no"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'addconvocatoria':
            try:
                eEvento = EventoFormacionEjecutiva.objects.get(pk=int(encrypt(request.POST['idc'])))
                f = DatosConvocatoriaForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})

                eConvocatoria = ConvocatoriaFormacionEjecutiva(
                    evento=eEvento,
                    numero=f.cleaned_data['numero'],
                    anio=f.cleaned_data['anio'],
                    descripcion=f.cleaned_data['nombre'],
                    alias=f.cleaned_data['alias'],
                )
                eConvocatoria.save(request)
                log(u'Añadió una conovocatoria de formación ejecutiva: %s' % eConvocatoria, request, "add")

                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos: {ex}'})

        elif action == 'addtiporubro':
            try:
                eConvocatoria = ConvocatoriaFormacionEjecutiva.objects.get(pk=int(request.POST['id']))
                f = DatosConvocatoriaRubroForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                if not eConvocatoria.tiporubro:
                    eTipo = TipoOtroRubro(nombre=f.cleaned_data['rubro'],
                                         partida_id=101,
                                         unidad_organizacional_id=165,
                                         programa_id=9,
                                         valor=f.cleaned_data['costo'],
                                         ivaaplicado_id=1,
                                         tiporubro=8)
                    eTipo.save(request)
                else:
                    eTipo = eConvocatoria.tiporubro
                    eTipo.nombre = f.cleaned_data['rubro']
                    eTipo.valor = f.cleaned_data['costo']
                    eTipo.save(request)

                eConvocatoria.tiporubro = eTipo
                eConvocatoria.costo = eTipo.valor
                eConvocatoria.save(request)
                log(u'Adicionó un tipo de rubro: %s' % eTipo, request, "add")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos: {ex}'})

        elif action == 'addfechas':
            try:
                eConvocatoria = ConvocatoriaFormacionEjecutiva.objects.get(pk=int(request.POST['id']))
                f = DatosConvocatoriaFechasForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})

                # Validación de fecha de inicio y fin de la convocatoria
                if f.cleaned_data['inicio'] >= f.cleaned_data['fin']:
                    return JsonResponse({'result': True,
                                         "mensaje": "La fecha de INICIO DE LA CONVOCATORIA no puede ser mayor o igual que la fecha FIN DE LA CONVOCATORIA."})

                # Validación de fecha de inicio y fin del periodo
                if f.cleaned_data['inicio_c'] >= f.cleaned_data['fin_c']:
                    return JsonResponse({'result': True,
                                         "mensaje": "La fecha de INICIO DEL EVENTO no puede ser mayor o igual que la fecha FIN DEL EVENTO."})

                # Validación cruzada: el EVENTO no puede iniciar si no ha finalizado la convocatoria
                if f.cleaned_data['inicio_c'] <= f.cleaned_data['fin']:
                    return JsonResponse({'result': True,
                                         "mensaje": "La fecha de INICIO DEL EVENTO no puede ser menor o igual que la fecha FIN DE LA CONVOCATORIA."})

                eConvocatoria.inicio = f.cleaned_data['inicio']
                eConvocatoria.fin = f.cleaned_data['fin']
                eConvocatoria.inicio_curso = f.cleaned_data['inicio_c']
                eConvocatoria.fin_curso = f.cleaned_data['fin_c']
                eConvocatoria.cupo = f.cleaned_data['cupo']
                eConvocatoria.save(request)
                log(u'Adicionó fechas de convocatoria: %s' % eConvocatoria, request, "add")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos: {ex}'})

        elif action == 'addpersona':
            try:
                f = RegistroFormacionEjecutivaForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['cedula'][:2] == u'VS' or f.cleaned_data['cedula'][:2] == u'vs':
                        # if not Persona.objects.filter(pasaporte=f.cleaned_data['cedula'][2:]).exists():
                        if not Persona.objects.filter(pasaporte=f.cleaned_data['cedula']).exists():
                            persona = Persona(pasaporte=f.cleaned_data['cedula'],
                                              nombres=f.cleaned_data['nombres'],
                                              apellido1=f.cleaned_data['apellido1'],
                                              apellido2=f.cleaned_data['apellido2'],
                                              email=f.cleaned_data['email'],
                                              telefono=f.cleaned_data['telefono'],
                                              sexo_id=request.POST['genero'],
                                              nacimiento='1999-01-01',
                                              direccion=request.POST['direccion'],
                                              direccion2=''
                                              )
                            persona.save(request)
                            # log(u'Adiciono persona formulario externo de admision posgrado: %s' % persona, request, "add")
                        else:
                            persona = Persona.objects.filter(pasaporte=f.cleaned_data['cedula']).last()
                            persona.email = f.cleaned_data['email']
                            persona.telefono = f.cleaned_data['telefono']
                            persona.direccion = request.POST['direccion']
                            persona.save(request)
                            # log(u'Editó persona: %s' % persona, request, "edit")
                    else:
                        if not Persona.objects.filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula']),status=True).exists():
                            persona = Persona(cedula=f.cleaned_data['cedula'],
                                              nombres=f.cleaned_data['nombres'],
                                              apellido1=f.cleaned_data['apellido1'],
                                              apellido2=f.cleaned_data['apellido2'],
                                              email=f.cleaned_data['email'],
                                              telefono=f.cleaned_data['telefono'],
                                              sexo_id=request.POST['genero'],
                                              nacimiento='1999-01-01',
                                              direccion=request.POST['direccion'],
                                              )
                            persona.save(request)
                            # log(u'Adiciono persona formulario externo de admision posgrado: %s' % persona, request, "add")
                        else:
                            persona = Persona.objects.filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula'])).first()
                            persona.email = f.cleaned_data['email']
                            persona.telefono = f.cleaned_data['telefono']
                            persona.direccion = request.POST['direccion']
                            persona.save(request)
                    return JsonResponse({'result': 'ok',"idpersona": persona.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'generarnombrescohorte':
            try:
                if 'numero' in request.POST:
                    if request.POST['numero'] == "" or request.POST['numero'] == '':
                        return JsonResponse({"result": "bad", "mensaje": f"Por favor, ingrese solo números enteros positivos. No se permiten caracteres especiales."})

                if 'anio' in request.POST:
                    if request.POST['anio'] == "" or request.POST['anio'] == '':
                        return JsonResponse({"result": "bad", "mensaje": f"Por favor, ingrese solo números enteros positivos. No se permiten caracteres especiales."})
                    if len(request.POST['anio']) != 4:
                        return JsonResponse({"result": "bad", "mensaje": f"Por favor, ingrese un año válido"})


                eAnio = int(request.POST['anio'])
                eNumero = int(request.POST['numero'])


                if eNumero > 10:
                    return JsonResponse({"result": "bad",
                                         "mensaje": f"El número ingresado no debe ser mayor a 10."})

                if eAnio < datetime.now().date().year:
                    return JsonResponse({"result": "bad",
                                         "mensaje": f"El año ingresado no puede ser menor al año actual"})

                if eAnio > 3000:
                    return JsonResponse({"result": "bad",
                                         "mensaje": f"Por favor, ingrese un año válido"})


                eEvento = EventoFormacionEjecutiva.objects.get(pk=int((request.POST['idc'])))

                if entero_a_romano(eNumero) == 'novalido':
                    return JsonResponse({"result": "bad", "mensaje": f"El número ingresado debe ser un entero positivo"})

                if ConvocatoriaFormacionEjecutiva.objects.filter(status=True, evento=eEvento, numero=eNumero, anio=eAnio).exists():
                    return JsonResponse({"result": "bad", "mensaje": f"Ya existe una convocatoria {eNumero} del año {eAnio} para el evento {eEvento}."})

                convocatoria = f'CONVOCATORIA {entero_a_romano(eNumero)}-{eAnio}'

                return JsonResponse({"result": "ok", "convocatoria": convocatoria})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'listarasignaturas':
            try:
                if 'id' in request.POST:
                    lista = []
                    idmallas = Malla.objects.filter(status=True, carrera__id=int(request.POST['id'])).values_list('id', flat=True).order_by('id').distinct()
                    eAsignaturas = AsignaturaMalla.objects.filter(status=True, malla__id__in=idmallas)
                    for eAsignatura in eAsignaturas:
                        lista.append([eAsignatura.id, f'{eAsignatura.id} - {eAsignatura.asignatura.nombre}'])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'listarmodulos':
            try:
                filtrado = request.POST['todos']
                lista = []
                if filtrado == 'si':
                    eMaterias = Materia.objects.filter(status=True, nivel__periodo__tipo__id=3, inicio__gte=datetime.now().date())
                else:
                    ida = int(request.POST['ida'])
                    idc = int(request.POST['idc'])
                    inicio = request.POST['inicio']
                    fin = request.POST['fin']

                    filtro = Q(status=True, nivel__periodo__tipo__id=3)
                    idc = int(request.POST['idc'])

                    if inicio !=  '':
                        filtro = filtro & (Q(inicio__gte=inicio))
                    else:
                        filtro = filtro & (Q(inicio__gte=datetime.now().date()))

                    if idc > 0:
                        filtro = filtro & (Q(asignaturamalla__malla__carrera__id=idc))

                    if ida > 0:
                        filtro = filtro & (Q(asignaturamalla__id=ida))

                    eMaterias = Materia.objects.filter(filtro)

                for eMateria in eMaterias:
                    eCohorte = CohorteMaestria.objects.filter(status=True, periodoacademico=eMateria.nivel.periodo).first()
                    lista.append([eMateria.id, f'{eMateria.id} - {eMateria.asignaturamalla.asignatura.nombre} - {eMateria.paralelo} - Inicio: {eMateria.inicio} | Fin: {eMateria.fin} - {eMateria.asignaturamalla.malla.carrera.__str__()} - {eCohorte.descripcion}'])
                return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'consultadatosasi':
            try:
                eAsignaturaMalla = AsignaturaMalla.objects.get(status=True, pk=int(request.POST['id']))

                return JsonResponse({"result": "ok", "creditos": eAsignaturaMalla.creditos, "horas": eAsignaturaMalla.horas, "nombre": eAsignaturaMalla.asignatura.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'consultafechas':
            try:
                inicio = fin = ''
                id = int(request.POST['id'])
                ini = request.POST['ini']
                fin = request.POST['fin']

                if id > 0:
                    eMateria = Materia.objects.get(status=True, pk=id)
                    inicio = eMateria.inicio
                    fin = eMateria.fin
                else:
                    if ini:
                        inicio = ini
                    if fin:
                        fin = fin
                return JsonResponse({"result": "ok", "inicio": inicio, "fin": fin})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'addmodulos':
            try:
                eConvocatoria = ConvocatoriaFormacionEjecutiva.objects.get(pk=int(request.POST['id']))
                form = ModulosConvocatoriaForm(request.POST)
                if 'carrera' in request.POST:
                    carrera = request.POST['carrera']
                    if carrera:
                        form.edit_carrera(int(request.POST['carrera']))

                if 'asignatura' in request.POST:
                    asignatura = request.POST['asignatura']
                    if asignatura:
                        form.edit_asignatura(int(request.POST['asignatura']))

                if 'profesor' in request.POST:
                    profesor = request.POST['profesor']
                    if profesor:
                        form.edit_profesor(int(request.POST['profesor']))

                horas = creditos = None
                carrera = asignatura = profesor = materias = None
                if form.is_valid():
                    nombre_a = form.cleaned_data['nombre']
                    inicio = form.cleaned_data['inicio']
                    fin = form.cleaned_data['fin']

                    if 'profesor' in request.POST:
                        profesor = request.POST['profesor']
                        if profesor:
                            profesor = form.cleaned_data['profesor']

                    if inicio >= fin:
                        return JsonResponse({'result': 'bad',
                                             "mensaje": f'Las fecha de inicio del módulo {nombre_a} no puede ser mayor o igual a la de fin'}, safe=False)

                    if form.cleaned_data['homologable']:
                        horas = form.cleaned_data['horas']
                        creditos = form.cleaned_data['creditos']
                        carrera = form.cleaned_data['carrera']
                        asignatura = form.cleaned_data['asignatura']

                    if DetalleAsignaturasFormacionEjecutiva.objects.filter(status=True, convocatoria=eConvocatoria,
                                                                           inicio__lt=fin, fin__gt=inicio).exists():
                        eDet = DetalleAsignaturasFormacionEjecutiva.objects.filter(status=True,
                                                                                   convocatoria=eConvocatoria,
                                                                                   inicio__lt=fin, fin__gt=inicio)
                        mensaje = ''
                        for eD in eDet:
                            mensaje += f'Módulo: {eD.nombre} - Inicio: {eD.inicio} - Fin: {eD.fin},'
                        return JsonResponse({'result': 'bad',
                                             "mensaje": f'Las fechas ingresadas tienen un conflicto con {mensaje}.'}, safe=False)

                    eDetalle = DetalleAsignaturasFormacionEjecutiva(nombre=nombre_a,
                                                                    convocatoria=eConvocatoria,
                                                                    carrera=carrera,
                                                                    asignaturamalla=asignatura,
                                                                    horas=horas,
                                                                    creditos=creditos,
                                                                    homologable=form.cleaned_data['homologable'],
                                                                    planificable=form.cleaned_data['planificable'],
                                                                    inicio=inicio,
                                                                    fin=fin)
                    eDetalle.save(request)

                    if profesor:
                        eInstructor = crear_instructor(request, profesor.id, eDetalle)
                        
                        
                        if eInstructor and form.cleaned_data['cursomoodle']:
                            asignar_modelo_eval(request, eInstructor.id)
                            modeloNotas = eInstructor.notaformacionejecutiva_set.filter(status=True).count()
                            if modeloNotas == 0:
                                return JsonResponse({'result': 'bad',
                                                     "mensaje": f'Asigne un modelo evaluativo al evento.'}, safe=False)
                            crear_curso_moodle(request, eInstructor.id)

                    if 'lista_items1' in request.POST and form.cleaned_data['planificable']:
                        for registro in json.loads(request.POST['lista_items1']):
                            materias = registro['materias']
                            if materias:
                                elementos = materias.split(',')
                                lista = [int(elemento) for elemento in elementos]
                                for idmateria in lista:
                                    eDetalle.materias.add(int(idmateria))

                    eDetalles = DetalleAsignaturasFormacionEjecutiva.objects.filter(status=True, convocatoria=eConvocatoria)
                    inicio_curso = eDetalles.order_by('inicio').first().inicio
                    fin_curso = eDetalles.order_by('-fin').first().fin

                    eConvocatoria = eDetalles.first().convocatoria
                    eConvocatoria.inicio_curso = inicio_curso
                    eConvocatoria.fin_curso = fin_curso
                    eConvocatoria.save(request)

                    log(u'Adicionó recursos del evento: %s' % eDetalle, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": f"Ha ocurrido un error {form.errors.items()}"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % (ex)})

        elif action == 'editarmodulo':
            try:
                eDetalle = DetalleAsignaturasFormacionEjecutiva.objects.get(status=True, pk=int(request.POST['id']))
                f = ModulosConvocatoriaForm(request.POST)
                if 'carrera' in request.POST:
                    if request.POST['carrera'] != '':
                        f.edit_carrera(int(request.POST['carrera']))
                if 'asignatura' in request.POST:
                    if request.POST['asignatura'] != '':
                        f.edit_asignatura(int(request.POST['asignatura']))
                if 'materias' in request.POST:
                    if request.POST['materias'] != '':
                        int_list = [int(num) for num in request.POST.getlist('materias')]
                        f.edit_materias(int_list)
                if not f.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": f"Error en el formulario {f.errors.items()}"})
                homologable = planificable = False
                horas = creditos = 0
                carrera = asignatura = profesor = materias = None
                if f.cleaned_data['homologable'] == True:
                    homologable = True
                    horas = int(f.cleaned_data['horas'])
                    creditos = int(f.cleaned_data['creditos'])
                    carrera = int(request.POST['carrera'])
                    asignatura = int(request.POST['asignatura'])

                    if f.cleaned_data['planificable'] == True:
                        planificable = True

                inicio = f.cleaned_data['inicio']
                fin = f.cleaned_data['fin']

                if request.POST['profesor'] != '':
                    profesor = int(request.POST['profesor'])

                if DetalleAsignaturasFormacionEjecutiva.objects.filter(status=True, convocatoria=eDetalle.convocatoria,
                                                                       inicio__lt=fin, fin__gt=inicio).exclude(pk=eDetalle.id).exists():
                    return JsonResponse({'result': True,
                                         "mensaje": f'Las fechas ingresadas tienen un conflicto con otra asignatura.'}, safe=False)

                eDetalle.nombre = f.cleaned_data['nombre']
                eDetalle.carrera_id = carrera
                eDetalle.asignaturamalla_id = asignatura
                eDetalle.horas = horas
                eDetalle.creditos = creditos
                eDetalle.homologable = homologable
                eDetalle.planificable = planificable
                eDetalle.inicio = inicio
                eDetalle.fin = fin
                eDetalle.profesor_id = profesor

                eDetalle.save(request)

                if f.cleaned_data['planificable'] == True:
                    materias = request.POST['materias']
                    if materias:
                        elementos = materias.split(',')
                        lista = [int(elemento) for elemento in elementos]
                        idact = eDetalle.materias.all().values_list('id', flat=True)

                        list_remove = []
                        for id in idact:
                            if id not in lista:
                                list_remove.append(id)

                        list_add = []
                        for idp in lista:
                            if idp not in idact:
                                list_add.append(idp)

                        for id in list_add:
                            eDetalle.materias.add(int(id))

                        for id in list_remove:
                            eDetalle.materias.remove(int(id))
                log(u'Adicionó recursos del evento: %s' % eDetalle, request, "add")
                return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'addmodeloevaluativo':
            try:
                form = ModeloEvaluativoFormacionEjecutivaForm(request.POST)
                if not form.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": f"Error en el formulario {form.errors.items()}"})

                modelo = ModeloEvaluativoFormacionEjecutiva(
                    nombre=form.cleaned_data['nombre'],
                    notaminima=form.cleaned_data['notaminima'],
                    notamaxima=form.cleaned_data['notamaxima'],
                    principal=form.cleaned_data['principal'],
                    evaluacion=form.cleaned_data['evaluacion']
                )
                modelo.save(request)
                log(u"Agregó modelo de formación ejecutiva: %s" % (modelo.__str__()), request, 'change')
                return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'addmodeloevaluativogeneral':
            try:
                form = ModeloEvaluativoFormacionGeneralEjecutivaForm(request.POST)
                form.adicionar()
                if not form.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": f"Error en el formulario {form.errors.items()}"})

                modelo = ModeloEvaluativoGeneralFormacionEjecutiva(
                    modelo=form.cleaned_data['modelo'],
                    orden=form.cleaned_data['orden']
                )
                modelo.save(request)
                log(u"Agregó modelo de formación ejecutiva general: %s" % (modelo.__str__()), request, 'change')
                return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'editmodeloevaluativo':
            try:
                eModelo = ModeloEvaluativoFormacionEjecutiva.objects.get(status=True, pk=int(request.POST['id']))

                form = ModeloEvaluativoFormacionEjecutivaForm(request.POST)
                if not form.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": f"Error en el formulario {form.errors.items()}"})

                eModelo.nombre = form.cleaned_data['nombre']
                eModelo.notaminima = form.cleaned_data['notaminima']
                eModelo.notamaxima = form.cleaned_data['notamaxima']
                eModelo.principal = form.cleaned_data['principal']
                eModelo.evaluacion = form.cleaned_data['evaluacion']

                eModelo.save(request)
                log(u"Actualizó modelo de formación ejecutiva: %s" % (eModelo.__str__()), request, 'change')
                return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'editmodeloevaluativogeneral':
            try:
                eModelo = ModeloEvaluativoGeneralFormacionEjecutiva.objects.get(status=True, pk=int(request.POST['id']))

                form = ModeloEvaluativoFormacionGeneralEjecutivaForm(request.POST)
                form.editar()
                if not form.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": f"Error en el formulario {form.errors.items()}"})

                eModelo.orden = form.cleaned_data['orden']
                eModelo.save(request)
                log(u"Actualizó modelo de formación ejecutiva general: %s" % (eModelo.__str__()), request, 'change')
                return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        elif action == 'deletemodelogeneral':
            try:
                eModelo = ModeloEvaluativoGeneralFormacionEjecutiva.objects.get(pk=int(request.POST['id']))
                eModelo.status = False
                eModelo.save(request)
                return JsonResponse({"result": 'ok', "mensaje": u"Solicitud eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'deletemodelo':
            try:
                eModelo = ModeloEvaluativoFormacionEjecutiva.objects.get(pk=int(request.POST['id']))
                eModelo.status = False
                eModelo.save(request)
                return JsonResponse({"result": 'ok', "mensaje": u"Solicitud eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'generate_certificate':
            try:
                data['eInscrito'] = eInscrito = InscripcionFormacionEjecutiva.objects.get(status=True, pk=int(request.POST['id']))
                # ruta = '/static/images/modelo.jpg'
                # data['rutaimg'] = (SITE_STORAGE + ruta).replace('\\', '/')
                import uuid
                data['elabora_persona'] = eInscrito.interesado.persona

                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                       "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"Milagro, %s de %s del %s" % (
                    datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                qrname = f'qr_certificado_fe_{eInscrito.id}'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_fe', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_fe')

                # Verifica si la carpeta existe, si no, la crea
                if not os.path.exists(folder):
                    os.makedirs(folder)

                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                # generar nombre html y url html
                if not eInscrito.namehtmlinsignia:
                    htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
                else:
                    htmlname = eInscrito.namehtmlinsignia
                urlname = "/media/qrcode/certificados_fe/%s" % htmlname
                rutahtml = SITE_STORAGE + urlname
                if os.path.isfile(rutahtml):
                    os.remove(rutahtml)
                # generar nombre html y url html
                # url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/certificados/' + htmlname)
                # url = pyqrcode.create(f'https://sga.unemi.edu.ec/media/qrcode/certificados/{htmlname}?v={data["version"]}')
                url = pyqrcode.create(dominio_sistema + '/media/qrcode/certificados_fe/' + htmlname)
                data['qrname'] = 'qr' + qrname

                data['urlhtmlinsignia'] = dominio_sistema + urlname
                valida = conviert_html_to_pdfsavevistaprevia_2('adm_formacionejecutiva/certificado_final.html',{'pagesize': 'A4', 'data': data}, qrname + '.pdf')
                if valida:
                    eInscrito.rutapdf = 'qrcode/certificados_fe/' + qrname + '.pdf'
                    eInscrito.save(request)
                    data['rutapdf'] = '/media/{}'.format(eInscrito.rutapdf)
                    data['idcertificado'] = htmlname[0:len(htmlname) - 5]
                    a = render(request, "adm_formacionejecutiva/certificado_confirm.html",
                               {"data": data, 'institucion': 'UNIVERSIDAD ESTATAL DE MILAGRO', "remotenameaddr": 'sga.unemi.edu.ec'})
                    with open(SITE_STORAGE + urlname, "wb") as f:
                        f.write(a.content)
                    f.close()
                    eInscrito.namehtmlinsignia = htmlname
                    eInscrito.urlhtmlinsignia = urlname
                    eInscrito.estado = 2
                    eInscrito.save(request)
                    # fin crear html en la media y guardar url en base
                    time.sleep(5)
                    return JsonResponse({"result": "ok", "url": eInscrito.rutapdf.url})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al generar el reporte."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Problemas al generar el reporte"})

        elif action == 'crearcursomoodle':
            try:
                eInstructor = InstructorFormacionEjecutiva.objects.get(status=True, activo=True, pk=int(request.POST['id']))
                crear_curso_moodle(request, eInstructor.id)
                return JsonResponse({"result": 'ok', "mensaje": u"Curso creado correctamente"})
            except Exception as ex:
                pass
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addevento':
                try:
                    data['title'] = 'Adicionar evento de formación ejecutiva'
                    form = EventoFormacionEjecutivaForm()
                    data['action'] = 'addevento'
                    data['form'] = form
                    return render(request, "adm_formacionejecutiva/addevento.html", data)
                    # template = get_template("adm_formacionejecutiva/modal/formmodal.html")
                    # return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editevento':
                try:
                    data['action'] = 'editevento'
                    eEvento = EventoFormacionEjecutiva.objects.get(status=True, pk=int(request.GET['id']))
                    data['id'] = eEvento.id
                    data['eEvento'] = eEvento

                    duracion_str = str(eEvento.duracion)

                    if 'day' in duracion_str:
                        days, time_str = duracion_str.split(', ')
                        days = int(days.split(' ')[0])
                        horas, minutos, segundos = map(int, time_str.split(':'))
                        horas += days * 24
                    else:
                        horas, minutos, segundos = map(int, duracion_str.split(':'))

                    form = EventoFormacionEjecutivaForm(initial={'nombre': eEvento.nombre,
                                                                'categoria': eEvento.categoria,
                                                                 'nivel': eEvento.nivel,
                                                                 'modalidad': eEvento.modalidad,
                                                                 'descripcion': eEvento.descripcion,
                                                                 'alias': eEvento.alias,
                                                                 'horas': horas,
                                                                 'minutos': minutos,
                                                                 'archivo': eEvento.banner,
                                                                 'activo': eEvento.activo})
                    data['form'] = form

                    template = get_template('adm_formacionejecutiva/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'convocatorias':
                try:
                    eEvento = EventoFormacionEjecutiva.objects.get(status=True, pk=int(request.GET['id']))
                    data['title'] = f'Convocatorias del evento {eEvento.nombre}'
                    url_vars = '&action=convocatorias&id=' + request.GET['id']
                    filtro = Q(status=True, evento_id=eEvento.id)

                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(descripcion__icontains=search) | Q(alias__icontains=search))
                        else:
                            filtro = filtro & (Q(descripcion__icontains=ss[0]) & Q(descripcion__icontains=ss[1]))
                        url_vars += f"&s={search}"

                    eConvocatorias = ConvocatoriaFormacionEjecutiva.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(eConvocatorias, 25)
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
                    data['eConvocatorias'] = page.object_list
                    data['url_vars'] = url_vars
                    data['id'] = int(request.GET['id'])
                    return render(request, "adm_formacionejecutiva/convocatorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'planficacionevento':
                try:
                    data['title'] = f'Planficación del evento'
                    eConvocatoria = ConvocatoriaFormacionEjecutiva.objects.get(status=True, pk=int(request.GET['id']))
                    data['eConvocatoria'] = eConvocatoria
                    data['eDetalles'] = DetalleAsignaturasFormacionEjecutiva.objects.filter(status=True, convocatoria=eConvocatoria).order_by('inicio')
                    return render(request, "adm_formacionejecutiva/planificacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarmodulo':
                try:
                    eDetalle = DetalleAsignaturasFormacionEjecutiva.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']

                    filtrado = False
                    # if eDetalle.materias.all():
                    #     filtrado = True

                    form = ModulosConvocatoriaForm(initial={'homologable': eDetalle.homologable,
                                                            'planificable': eDetalle.planificable,
                                                            # 'carrera': eDetalle.carrera,
                                                            # 'asignatura': eDetalle.asignaturamalla,
                                                            'nombre': eDetalle.nombre,
                                                            'horas': eDetalle.horas,
                                                            'creditos': eDetalle.creditos,
                                                            'inicio': eDetalle.inicio,
                                                            'fin': eDetalle.fin,
                                                            # 'materias': eDetalle.materias.all(),
                                                            # 'profesor': eDetalle.profesor,
                                                            'filtrado': filtrado})
                    if eDetalle.carrera:
                        form.edit_carrera(eDetalle.carrera.id)
                    else:
                        form.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id')

                    if eDetalle.asignaturamalla:
                        form.edit_asignatura(eDetalle.asignaturamalla.id)
                    if eDetalle.profesor:
                        form.edit_profesor(eDetalle.profesor.id)

                    if eDetalle.materias.all():
                        idm = eDetalle.materias.all().values_list('id', flat=True)
                        form.edit_materias(idm)

                    data['form'] = form
                    data['id'] = eDetalle.id
                    template = get_template("adm_formacionejecutiva/modal/formmodulo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addmodeloevaluativo':
                try:
                    data['action'] = request.GET['action']
                    form = ModeloEvaluativoFormacionEjecutivaForm()
                    data['form'] = form
                    template = get_template("adm_formacionejecutiva/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addmodeloevaluativogeneral':
                try:
                    data['action'] = request.GET['action']
                    form = ModeloEvaluativoFormacionGeneralEjecutivaForm()
                    form.adicionar()
                    idm = ModeloEvaluativoGeneralFormacionEjecutiva.objects.filter(status=True).values_list('modelo__id')
                    form.fields['modelo'].queryset = ModeloEvaluativoFormacionEjecutiva.objects.filter(status=True).exclude(id__in=idm)
                    data['form'] = form
                    template = get_template("adm_formacionejecutiva/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editmodeloevaluativo':
                try:
                    eModelo = ModeloEvaluativoFormacionEjecutiva.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = ModeloEvaluativoFormacionEjecutivaForm(initial={'nombre': eModelo.nombre,
                                                                           'notaminima': eModelo.notaminima,
                                                                           'notamaxima': eModelo.notamaxima,
                                                                           'principal': eModelo.principal,
                                                                           'evaluacion': eModelo.evaluacion})
                    data['form'] = form
                    data['id'] = eModelo.id
                    template = get_template("adm_formacionejecutiva/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editmodeloevaluativogeneral':
                try:
                    eModelo = ModeloEvaluativoGeneralFormacionEjecutiva.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = ModeloEvaluativoFormacionGeneralEjecutivaForm(initial={'modelo_a': eModelo.__str__(),
                                                                                  'orden': eModelo.orden})
                    form.editar()
                    data['form'] = form
                    data['id'] = eModelo.id
                    template = get_template("adm_formacionejecutiva/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'listadoinscritos':
                try:
                    eConvocatoria = ConvocatoriaFormacionEjecutiva.objects.get(status=True, pk=int(request.GET['id']))
                    data['title'] = f'Listado de inscritos'
                    data['eConvocatoria'] = eConvocatoria
                    url_vars = '&action=listadoinscritos&id=' + request.GET['id']
                    filtro = Q(status=True, convocatoria=eConvocatoria)

                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(persona__apellido1__icontains=search) |
                                                     Q(persona__apellido2__icontains=search) |
                                                     Q(persona__nombres__icontains=search) |
                                                     Q(persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(persona__apellido1__icontains=ss[0]) &
                                                     Q(persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(persona__apellido1__icontains=ss[0]) &
                                                Q(persona__apellido2__icontains=ss[1]) &
                                               Q(persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    eInscritos = InscripcionFormacionEjecutiva.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(eInscritos, 25)
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
                    data['eInscritos'] = page.object_list
                    data['url_vars'] = url_vars
                    data['id'] = int(request.GET['id'])
                    return render(request, "adm_formacionejecutiva/listadoinscritos.html", data)
                except Exception as ex:
                    pass

            if action == 'addevento':
                try:
                    form = EventoFormacionEjecutivaForm()
                    data['action'] = 'addevento'
                    data['form'] = form
                    template = get_template("adm_formacionejecutiva/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addconvocatoria':
                try:
                    eEvento = EventoFormacionEjecutiva.objects.get(pk=int(encrypt(request.GET['idc'])))
                    form = DatosConvocatoriaForm(initial={'evento': eEvento.nombre})
                    data['form'] = form
                    data['action'] = 'addconvocatoria'
                    data['idc'] = eEvento.id
                    template = get_template('adm_formacionejecutiva/modal/formdatosconvocatoria.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addtiporubro':
                try:
                    eConvocatoria = ConvocatoriaFormacionEjecutiva.objects.get(pk=int(request.GET['id']))
                    eRubro = f'{eConvocatoria.evento.nombre} - {eConvocatoria.descripcion}'
                    form = DatosConvocatoriaRubroForm(initial={'evento': eConvocatoria.evento.nombre,
                                                               'convocatoria': eConvocatoria.descripcion,
                                                               'rubro': eRubro,
                                                               'tipo': 'FORMACIÓN EJECUTIVA',
                                                               'costo': eConvocatoria.tiporubro.valor if eConvocatoria.tiporubro else None})
                    data['form'] = form
                    data['action'] = 'addtiporubro'
                    data['id'] = eConvocatoria.id
                    template = get_template('adm_formacionejecutiva/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addfechas':
                try:
                    eConvocatoria = ConvocatoriaFormacionEjecutiva.objects.get(pk=int(request.GET['id']))
                    form = DatosConvocatoriaFechasForm(initial={'evento': eConvocatoria.evento.nombre,
                                                               'convocatoria': eConvocatoria.descripcion,
                                                               'inicio': eConvocatoria.inicio,
                                                               'fin': eConvocatoria.fin,
                                                               'inicio_c': eConvocatoria.inicio_curso,
                                                               'fin_c': eConvocatoria.fin_curso,
                                                               'cupo': eConvocatoria.cupo})
                    data['form'] = form
                    data['action'] = 'addfechas'
                    data['id'] = eConvocatoria.id
                    template = get_template('adm_formacionejecutiva/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addmodulos':
                try:
                    eConvocatoria = ConvocatoriaFormacionEjecutiva.objects.get(pk=int(request.GET['id']))
                    data['title'] = f'Adicionar modulo del evento {eConvocatoria.evento.nombre} - {eConvocatoria.descripcion}'
                    form = ModulosConvocatoriaForm()
                    data['form'] = form
                    form.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id')

                    data['id'] = int(request.GET['id'])
                    data['eConvocatoria'] = eConvocatoria
                    return render(request, "adm_formacionejecutiva/addmodulos.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewmodelosevaluativosgeneral':
                try:
                    data['title'] = u'Modelo Evaluativo General'
                    url_vars = ''
                    url_vars += f'&action={action}'
                    filtro = Q(status=True)

                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(modelo__nombre__icontains=search))
                        else:
                            filtro = filtro & (Q(modelo__nombre__icontains=ss[0]) & Q(modelo__nombre__icontains=ss[1]))
                        url_vars += f"&s={search}"

                    eModelos = ModeloEvaluativoGeneralFormacionEjecutiva.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(eModelos, 25)
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
                    data['eModelos'] = page.object_list
                    data["url_vars"] = url_vars
                    data["url_params"] = url_vars
                    data["count"] = eModelos.count()
                    return render(request, "adm_formacionejecutiva/modeloevaluativogeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewmodelosevaluativos':
                try:
                    data['title'] = u'Modelos evaluativo'
                    url_vars = ''
                    filtro = Q(status=True)

                    url_vars += f'&action={action}'

                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(nombre__icontains=search))
                        else:
                            filtro = filtro & (Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]))
                        url_vars += f"&s={search}"

                    eModelos = ModeloEvaluativoFormacionEjecutiva.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(eModelos, 25)
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
                    data['eModelos'] = page.object_list
                    data["url_vars"] = url_vars
                    data["url_params"] = url_vars
                    data["count"] = eModelos.count()
                    return render(request, "adm_formacionejecutiva/modelosevaluativos.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarprofesor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Persona.objects.filter(Q(apellido1__icontains=s[0])
                                                      | Q(apellido2__icontains=s[0])
                                                      | Q(cedula__icontains=s[0])
                                                      | Q(pasaporte__icontains=s[0])
                                                      | Q(ruc__icontains=s[0]),
                                                      status=True).order_by('apellido1', 'apellido2', 'nombres')
                    else:
                        personas = Persona.objects.filter(Q(apellido1__icontains=s[0]) & Q(apellido2__icontains=s[1]),
                                                           status=True).order_by('apellido1', 'apellido2', 'nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.nombre_completo_inverso())} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'validaringreso':
                try:
                    materia = ''
                    eProfesorM = None

                    idm = request.GET['idm']
                    if idm != '':
                        idm = int(idm)

                        eMat = Materia.objects.get(pk=idm)

                        eProfesorM = ProfesorMateria.objects.filter(status=True, materia=eMat, tipoprofesor__id=11).first()
                        materia += f"{capitalize_first_letter(eMat.asignatura.nombre)} - {eMat.paralelo}"

                    idp = int(request.GET['idp'])
                    if idp > 0:
                        eProfesor = capitalize_first_letter(Profesor.objects.get(pk=int(idp)).persona.__str__())
                    elif eProfesorM:
                        eProfesor = capitalize_first_letter(eProfesorM.profesor.persona.__str__())
                    else:
                        eProfesor = 'Por definir'

                    res_js = {"result": True, 'materias': materia, 'profesor': eProfesor}
                except Exception as ex:
                    import sys
                    line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(line_error)
                    res_js = {"result":False,"mensaje":"Ocurrio un error!. Detalle: %s"% ex.__str__(),"line_erro":line_error}
                return JsonResponse(res_js)

            elif action == 'validarobj':
                try:
                    res_js = {"result": True}
                except Exception as ex:
                    import sys
                    line_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print(line_error)
                    res_js = {"result":False,"mensaje":"Ocurrio un error!. Detalle: %s"% ex.__str__(),"line_erro":line_error}
                return JsonResponse(res_js)

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Eventos de formación ejecutiva'
                url_vars = ''
                filtro = Q(status=True)
                idc = request.GET.get('idc', '0')

                search = None
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    if len(ss) == 1:
                        filtro = filtro & (Q(nombre__icontains=search) | Q(alias__icontains=search))
                    else:
                        filtro = filtro & (Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]))
                    url_vars += f"&s={search}"

                if int(idc) > 0:
                    filtro = filtro & (Q(categoria__id=idc))
                    data['idc'] = int(idc)
                    url_vars += f"&idc={idc}"

                eEventos = EventoFormacionEjecutiva.objects.filter(filtro).order_by('-id')
                paging = MiPaginador(eEventos, 25)
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
                data['eEventos'] = page.object_list
                data["url_vars"] = url_vars
                data["url_params"] = url_vars
                data["count"] = eEventos.count()
                data["eCategorias"] = CategoriaEventoFormacionEjecutiva.objects.filter(status=True)
                return render(request, "adm_formacionejecutiva/view.html", data)
            except Exception as ex:
                pass

def capitalize_first_letter(string):
    if not string:
        return string  # Manejo de cadena vacía
    return string[0].upper() + string[1:].lower()

def crear_instructor(request, idp, eDetalle):
    try:
        eInstructor = None
        ePersona = Persona.objects.get(status=True, pk=idp)
        if not InstructorFormacionEjecutiva.objects.filter(asignaturaform=eDetalle,
                                                            instructor=ePersona,
                                                            status=True).exists():
            eInstructor = InstructorFormacionEjecutiva(asignaturaform=eDetalle,
                                                       instructor=ePersona,
                                                       activo=True)
            eInstructor.save(request)

            if not eInstructor.tiene_perfilusuario():
                eInstructor.crear_eliminar_perfil_instructor(True)
        return eInstructor
    except Exception as ex:
        pass

def asignar_modelo_eval(request, idins):
    try:
        eInstructor = InstructorFormacionEjecutiva.objects.get(pk=idins)
        filtro = ModeloEvaluativoGeneralFormacionEjecutiva.objects.filter(status=True).order_by('orden')
    
        for f in filtro:
            if not NotaFormacionEjecutiva.objects.filter(status=True, modelo=f.modelo, instructor=eInstructor).exists():
                modelonota = NotaFormacionEjecutiva(modelo=f.modelo,
                                                   fecha=datetime.now().date(),
                                                   instructor=eInstructor)
                modelonota.save(request)
                log(u'Adiciono Modelo Evaluativo Instructor Formación Ejecutiva: %s' % modelonota, request, "add")
    except Exception as ex:
        pass


def crear_curso_moodle(request, idins):
    try:
        from django.db import connections
        eInstructor = InstructorFormacionEjecutiva.objects.get(pk=idins)

        curso = eInstructor.asignaturaform.convocatoria
        listadocodigo = curso.list_inscritos_costo().values_list('interesado__persona__idusermoodleposgrado', flat=True)

        cursorpos = connections['moodle_pos'].cursor()
        if len(listadocodigo) > 1:
            # Usar la cláusula IN para múltiples IDs
            placeholders = ','.join(['%s'] * len(listadocodigo))  # Crea los placeholders necesarios para la cláusula IN
            sql = """SELECT DISTINCT ARRAY_TO_STRING(array_agg(us1.id), ',')
                     FROM mooc_role_assignments asi
                     INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID
                     INNER JOIN mooc_user us1 ON us1.id=asi.userid
                     WHERE ASI.ROLEID = %s AND CON.INSTANCEID = %s AND us1.id IN (%s)""" % (10, eInstructor.idcursomoodle, placeholders)
            cursorpos.execute(sql, list(listadocodigo))
        else:
            # Usar = para un solo ID
            sql = """SELECT DISTINCT ARRAY_TO_STRING(array_agg(us1.id), ',')
                     FROM mooc_role_assignments asi
                     INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID
                     INNER JOIN mooc_user us1 ON us1.id=asi.userid
                     WHERE ASI.ROLEID = %s AND CON.INSTANCEID = %s AND us1.id = %s""" % (10, eInstructor.idcursomoodle, listadocodigo[0])
            cursorpos.execute(sql)
        row = cursorpos.fetchall()
        listadosmoodle = []
        if eInstructor.idcursomoodle:
            if row[0][0]:
                listadosmoodle = row[0][0].split(",")
        listac = None
        listacurso = curso.list_inscritos_costo()

        listac = listacurso.values_list('id', flat=True).exclude(interesado__persona__idusermoodleposgrado__in=listadosmoodle).order_by('interesado__persona__apellido1',
                                                                                                            'interesado__persona__apellido2',
                                                                                                            'interesado__persona__nombres')

        for idi in listac:
            eInscripcion = InscripcionFormacionEjecutiva.objects.get(status=True, pk=idi)
            eInscripcion.encursomoodle = True
            eInscripcion.save(request)
            eInstructor.crear_curso_moodle(eInscripcion.id, 0, formeje=True)
            time.sleep(3)

        cursorpos.close()
        return True
    except Exception as ex:
        pass