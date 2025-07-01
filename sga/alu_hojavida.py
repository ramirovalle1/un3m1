# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.datetime_safe import datetime
from decorators import secure_module, last_access
from med.models import PersonaExtension
from mobile.views import make_thumb_picture
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, ACTUALIZAR_FOTO_ALUMNOS
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import PersonaForm, CargarFotoForm, SeguimientoEstudianteForm, EstudioInscripcionSuperiorForm, \
    IdiomaDominaForm, ConocimientoInformaticoForm, ReferenciaPersonaForm, ConocimientoForm
from sga.funciones import generar_nombre, log
from sga.models import Persona, FotoPersona, SeguimientoEstudiante, EstudioInscripcion, IdiomaDomina, \
    NIVEL_CONOCIMIENTO, ConocimientoInformatico, CategoriaHerramienta, ReferenciaPersona, ConocimientoAdiconal


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'delidioma':
                try:
                    idioma = IdiomaDomina.objects.get(pk=request.POST['id'])
                    log(u"Elimino idioma: %s" % idioma, request, "del")
                    idioma.delete()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

            if action == 'editidioma':
                try:
                    idioma = IdiomaDomina.objects.get(pk=request.POST['id'])
                    f = IdiomaDominaForm(request.POST)
                    if f.is_valid():
                        idioma.idioma = f.cleaned_data['idioma']
                        idioma.oral = f.cleaned_data['oral']
                        idioma.lectura = f.cleaned_data['lectura']
                        idioma.escritura = f.cleaned_data['escritura']
                        idioma.save(request)
                        log(u"Edito idioma domina en hoja de vida: %s [%s]" % (idioma, idioma.id), request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error: Al editar datos'})

            if action == 'addidioma':
                try:
                    persona = request.session['persona']
                    f = IdiomaDominaForm(request.POST)
                    if f.is_valid():
                        idioma = IdiomaDomina(persona=persona,
                                              idioma=f.cleaned_data['idioma'],
                                              lectura=f.cleaned_data['lectura'],
                                              oral=f.cleaned_data['oral'],
                                              escritura=f.cleaned_data['escritura'])
                        idioma.save(request)
                        log(u'Adiciono idioma: %s' % idioma, request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            if action == 'delestudio':
                try:
                    estudio = EstudioInscripcion.objects.get(pk=request.POST['id'])
                    log(u'Elimino estudio: %s' % estudio, request, "del")
                    estudio.delete()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

            if action == 'delreferencia':
                try:
                    referencia = ReferenciaPersona.objects.get(pk=request.POST['id'])
                    log(u'Elimino referencia: %s' % referencia, request, "del")
                    referencia.delete()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

            if action == 'editestudio':
                try:
                    estudio = EstudioInscripcion.objects.get(pk=request.POST['id'])
                    f = EstudioInscripcionSuperiorForm(request.POST)
                    if f.is_valid():
                        estudio.universidad = f.cleaned_data['superiores']
                        estudio.carrera = f.cleaned_data['carrera']
                        estudio.titulo = f.cleaned_data['titulo']
                        estudio.anoestudio = f.cleaned_data['anoestudio']
                        estudio.graduado = f.cleaned_data['graduado']
                        estudio.estudiosposteriores = f.cleaned_data['posteriores']
                        estudio.incorporacion = f.cleaned_data['incorporacion']
                        estudio.save(request)
                        log(u"Edito estudio en hoja de vida: %s [%s]" % (estudio, estudio.id), request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error: al editar'})

            if action == 'delconocimiento':
                try:
                    conocimiento = ConocimientoInformatico.objects.get(pk=request.POST['id'])
                    log(u'Elimino conocimiento: %s' % conocimiento, request, "del")
                    conocimiento.delete()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

            if action == 'editconocimiento':
                try:
                    conocimiento = ConocimientoInformatico.objects.get(pk=request.POST['id'])
                    f = ConocimientoInformaticoForm(request.POST)
                    if f.is_valid():
                        conocimiento.herramienta = f.cleaned_data['herramienta']
                        conocimiento.descripcion = f.cleaned_data['descripcion']
                        conocimiento.nivel = int(f.cleaned_data['nivel'])
                        conocimiento.save(request)
                        log(u'Modifico conocimiento: %s' % conocimiento, request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error: al editar'})

            if action == 'editconocimientoadicional':
                try:
                    conocimiento = ConocimientoAdiconal.objects.get(pk=request.POST['id'])
                    f = ConocimientoForm(request.POST)
                    if f.is_valid():
                        conocimiento.nombre = f.cleaned_data['nombre']
                        conocimiento.descripcion = f.cleaned_data['descripcion']
                        conocimiento.save(request)
                        log(u'Modifico conocimiento adicional: %s' % conocimiento, request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error: al editar'})

            if action == 'delconocimientoadicional':
                try:
                    conocimiento = ConocimientoAdiconal.objects.get(pk=request.POST['id'])
                    log(u"Elimino conocimiento adicional: %s" % conocimiento, request, "del")
                    conocimiento.delete()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

            if action == 'editreferencia':
                try:
                    referencia = ReferenciaPersona.objects.get(pk=request.POST['id'])
                    f = ReferenciaPersonaForm(request.POST)
                    if f.is_valid():
                        referencia.nombres = f.cleaned_data['nombres']
                        referencia.apellidos = f.cleaned_data['apellidos']
                        referencia.email = f.cleaned_data['email']
                        referencia.telefono = f.cleaned_data['telefono']
                        referencia.institucion = f.cleaned_data['institucion']
                        referencia.relacion = f.cleaned_data['relacion']
                        referencia.save(request)
                        log(u'Modifico referencia: %s' % referencia, request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error: al editar'})

            if action == 'addconocimiento':
                try:
                    persona = request.session['persona']
                    f = ConocimientoInformaticoForm(request.POST)
                    if f.is_valid():
                        conocimiento = ConocimientoInformatico(persona=persona,
                                                               herramienta=f.cleaned_data['herramienta'],
                                                               descripcion=f.cleaned_data['descripcion'],
                                                               nivel=int(f.cleaned_data['nivel']))
                        conocimiento.save(request)
                        log(u'Adiciono conocimiento informatico: %s' % conocimiento, request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            if action == 'addconocimientoadicional':
                try:
                    persona = request.session['persona']
                    f = ConocimientoForm(request.POST)
                    if f.is_valid():
                        conocimiento = ConocimientoAdiconal(persona=persona,
                                                            nombre=f.cleaned_data['nombre'],
                                                            descripcion=f.cleaned_data['descripcion'])
                        conocimiento.save(request)
                        log(u'Adiciono conocimiento adicional: %s' % conocimiento, request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            if action == 'addestudio':
                try:
                    persona = request.session['persona']
                    f = EstudioInscripcionSuperiorForm(request.POST)
                    if f.is_valid():
                        estudio = EstudioInscripcion(persona=persona,
                                                     universidad=f.cleaned_data['superiores'],
                                                     carrera=f.cleaned_data['carrera'],
                                                     titulo=f.cleaned_data['titulo'],
                                                     anoestudio=f.cleaned_data['anoestudio'],
                                                     graduado=f.cleaned_data['graduado'],
                                                     estudiosposteriores=f.cleaned_data['posteriores'],
                                                     incorporacion=f.cleaned_data['incorporacion'])
                        estudio.save(request)
                        log(u'Adiciono estudio: %s' % estudio, request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            if action == 'addreferencia':
                try:
                    persona = request.session['persona']
                    f = ReferenciaPersonaForm(request.POST)
                    if f.is_valid():
                        referencia = ReferenciaPersona(persona=persona,
                                                       nombres=f.cleaned_data['nombres'],
                                                       apellidos=f.cleaned_data['apellidos'],
                                                       email=f.cleaned_data['email'],
                                                       telefono=f.cleaned_data['telefono'],
                                                       institucion=f.cleaned_data['institucion'],
                                                       relacion=f.cleaned_data['relacion'])
                        referencia.save(request)
                        log(u'Adiciono referencia: %s' % referencia, request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            if action == 'addexperiencia':
                try:
                    persona = request.session['persona']
                    f = SeguimientoEstudianteForm(request.POST)
                    if f.is_valid():
                        if not f.cleaned_data['labora']:
                            if f.cleaned_data['fecha'] >= f.cleaned_data['fechafin']:
                                return JsonResponse({'result': 'bad', 'mensaje': u'Error: La fecha fin es menor o igual a la fecha de inicio'})
                        seguimiento = SeguimientoEstudiante(persona=persona,
                                                            empresa=f.cleaned_data['empresa'],
                                                            industria=f.cleaned_data['industria'],
                                                            cargo=f.cleaned_data['cargo'],
                                                            ocupacion=f.cleaned_data['ocupacion'],
                                                            responsabilidades=f.cleaned_data['responsabilidades'],
                                                            telefono=f.cleaned_data['telefono'],
                                                            email=f.cleaned_data['email'],
                                                            sueldo=f.cleaned_data['sueldo'],
                                                            ejerce=f.cleaned_data['ejerce'],
                                                            fecha=f.cleaned_data['fecha'])
                        if not f.cleaned_data['labora']:
                            seguimiento.fechafin = f.cleaned_data['fechafin']
                        seguimiento.save(request)
                        log(u'Adiciono seguimiento laboral: %s' % seguimiento, request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar datos'})

            if action == 'delexperiencia':
                try:
                    experiencia = SeguimientoEstudiante.objects.get(pk=request.POST['id'])
                    log(u'Elimino seguimiento laboral: %s' % experiencia, request, "del")
                    experiencia.delete()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

            if action == 'editexperiencia':
                try:
                    experiencia = SeguimientoEstudiante.objects.get(pk=request.POST['id'])
                    f = SeguimientoEstudianteForm(request.POST)
                    if f.is_valid():
                        if not f.cleaned_data['labora']:
                            if f.cleaned_data['fecha'] >= f.cleaned_data['fechafin']:
                                return JsonResponse({'result': 'bad', 'mensaje': u'La fecha fin es menor o igual a la fecha de inicio'})
                        experiencia.empresa = f.cleaned_data['empresa']
                        experiencia.industria = f.cleaned_data['industria']
                        experiencia.cargo = f.cleaned_data['cargo']
                        experiencia.ocupacion = f.cleaned_data['ocupacion']
                        experiencia.responsabilidades = f.cleaned_data['responsabilidades']
                        experiencia.telefono = f.cleaned_data['telefono']
                        experiencia.email = f.cleaned_data['email']
                        experiencia.sueldo = f.cleaned_data['sueldo']
                        experiencia.ejerce = f.cleaned_data['ejerce']
                        experiencia.fecha = f.cleaned_data['fecha']
                        if not f.cleaned_data['labora']:
                            experiencia.fechafin = f.cleaned_data['fechafin']
                        else:
                            experiencia.fechafin = None
                        experiencia.save(request)
                        log(u'Modifico seguimiento laboral: %s' % experiencia, request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error: al editar'})

            if action == 'cargarfoto':
                try:
                    form = CargarFotoForm(request.POST, request.FILES)
                    if form.is_valid():
                        persona = request.session['persona']
                        foto = persona.foto()
                        nfile = request.FILES['foto']
                        nfile._name = generar_nombre("foto_", nfile._name)
                        if foto is not None:
                            foto.foto = nfile
                        else:
                            foto = FotoPersona(persona=persona,
                                               foto=nfile)
                        foto.save(request)
                        log(u'Cargo foto alumno de hoja de vida : %s' % foto, request, "edit")
                        make_thumb_picture(persona)
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"La imagen seleccionada no cumple los requisitos, de tamaño o formato o hubo un error al guardar fichero."})

            if action == 'editdatos':
                try:
                    personasession = request.session['persona']
                    persona = Persona.objects.get(pk=personasession.id)
                    f = PersonaForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['nombres']:
                            persona.nombres = f.cleaned_data['nombres']
                        if f.cleaned_data['apellido1']:
                            persona.apellido1 = f.cleaned_data['apellido1']
                        if f.cleaned_data['apellido2']:
                            persona.apellido2 = f.cleaned_data['apellido2']
                        if f.cleaned_data['cedula']:
                            persona.cedula = f.cleaned_data['cedula']
                        if f.cleaned_data['nacimiento']:
                            persona.nacimiento = f.cleaned_data['nacimiento']
                        persona.paisnacimiento = f.cleaned_data['paisnacimiento']
                        persona.provincianacimiento = f.cleaned_data['provincianacimiento']
                        persona.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                        persona.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                        persona.pais = f.cleaned_data['pais']
                        persona.provincia = f.cleaned_data['provincia']
                        persona.canton = f.cleaned_data['canton']
                        persona.parroquia = f.cleaned_data['parroquia']
                        persona.pasaporte = f.cleaned_data['pasaporte']
                        persona.sexo = f.cleaned_data['sexo']
                        persona.direccion = f.cleaned_data['direccion']
                        persona.direccion2 = f.cleaned_data['direccion2']
                        persona.num_direccion = f.cleaned_data['num_direccion']
                        persona.sector = f.cleaned_data['sector']
                        persona.ciudad = f.cleaned_data['cantonnac']
                        persona.telefono = f.cleaned_data['telefono']
                        persona.telefono_conv = f.cleaned_data['telefono_conv']
                        persona.email = f.cleaned_data['email']
                        perfil = persona.mi_perfil()
                        perfil.raza = f.cleaned_data['etnia']
                        perfil.save(request)
                        if not EMAIL_INSTITUCIONAL_AUTOMATICO:
                            persona.emailinst = f.cleaned_data['emailinst']
                        persona.sangre = f.cleaned_data['sangre']
                        if persona.personaextension_set.exists():
                            extra = persona.personaextension_set.all()[0]
                            extra.estadocivil = f.cleaned_data['estadocivil']
                            extra.save(request)
                        else:
                            extra = PersonaExtension(persona=persona,
                                                     estadocivil=f.cleaned_data['estadocivil'])
                            extra.save(request)
                        persona.save(request)
                        request.session['persona'] = persona
                        log(u'Edito datos personales alumno en hoja de vida : %s [%s]- perfil: %s' % (persona,persona.id,perfil), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar datos."})

            if action == 'addidioma':
                try:
                    personasession = request.session['persona']
                    form = IdiomaDominaForm(request.POST)
                    if form.is_valid():
                        idioma = IdiomaDomina(persona=persona,
                                              idioma=form.cleaned_data['idioma'],
                                              lectura=form.cleaned_data['lectura'],
                                              escritura=form.cleaned_data['escritura'])
                        idioma.save(request)
                        log(u'Adiciono idioma que domina: %s' % idioma, request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'delidioma':
                try:
                    data['title'] = u'Eliminar idioma'
                    data['idioma'] = persona.idiomadomina_set.get(pk=request.GET['id'])
                    return render(request, "alu_hojavida/delidioma.html", data)
                except Exception as ex:
                    pass

            if action == 'editidioma':
                try:
                    data['title'] = u'Editar Idioma'
                    data['idioma'] = idioma = persona.idiomadomina_set.get(pk=request.GET['id'])
                    data['form'] = IdiomaDominaForm(initial={'idioma': idioma.idioma,
                                                             'escritura': idioma.escritura,
                                                             'oral': idioma.oral,
                                                             'lectura': idioma.lectura})
                    return render(request, "alu_hojavida/editidioma.html", data)
                except Exception as ex:
                    pass

            if action == 'addidioma':
                try:
                    data['title'] = u'Adicionar idioma'
                    data['form'] = IdiomaDominaForm()
                    return render(request, "alu_hojavida/addidioma.html", data)
                except Exception as ex:
                    pass

            if action == 'cargarfoto':
                try:
                    data['title'] = u"Cargar foto"
                    data['form'] = CargarFotoForm()
                    return render(request, "alu_hojavida/cargarfoto.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatos':
                try:
                    data['title'] = u'Modificar datos de personales'
                    datosextension = persona.datos_extension()
                    form = PersonaForm(initial={'nombres': persona.nombres,
                                                'apellido1': persona.apellido1,
                                                'apellido2': persona.apellido2,
                                                'cedula': persona.cedula,
                                                'pasaporte': persona.pasaporte,
                                                'nacimiento': persona.nacimiento,
                                                'paisnacimiento': persona.paisnacimiento,
                                                'provincianacimiento': persona.provincianacimiento,
                                                'cantonnacimiento': persona.cantonnacimiento,
                                                'parroquianacimiento': persona.parroquianacimiento,
                                                'sexo': persona.sexo,
                                                'nacionalidad': persona.nacionalidad,
                                                'pais': persona.pais,
                                                'provincia': persona.provincia,
                                                'canton': persona.canton,
                                                'parroquia': persona.parroquia,
                                                'direccion': persona.direccion,
                                                'direccion2': persona.direccion2,
                                                'num_direccion': persona.num_direccion,
                                                'sector': persona.sector,
                                                'ciudad': persona.ciudad,
                                                'telefono': persona.telefono,
                                                'telefono_conv': persona.telefono_conv,
                                                'email': persona.email,
                                                'emailinst': persona.emailinst,
                                                'etnia': persona.mi_perfil().raza,
                                                'sangre': persona.sangre,
                                                'estadocivil': datosextension.estadocivil})
                    form.editar(persona)
                    if EMAIL_INSTITUCIONAL_AUTOMATICO:
                        form.sin_emailinst()
                    data['form'] = form
                    data['actualizar_foto_alumnos'] = ACTUALIZAR_FOTO_ALUMNOS
                    return render(request, "alu_hojavida/editdatos.html", data)
                except Exception as ex:
                    pass

            if action == 'delexperiencia':
                try:
                    data['title'] = u'Borrar experiencia de trabajo'
                    data['experiencia'] = SeguimientoEstudiante.objects.get(pk=request.GET['id'])
                    return render(request, "alu_hojavida/delexperiencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addexperiencia':
                try:
                    data['title'] = u'Adicionar Experiencia Laboral'
                    data['form'] = SeguimientoEstudianteForm(initial={'fecha': datetime.now().date(),
                                                                      'labora': True})
                    return render(request, "alu_hojavida/addexperiencia.html", data)
                except Exception as ex:
                    pass

            if action == 'delconocimiento':
                try:
                    data['title'] = u'Eliminar conocimiento'
                    data['conocimiento'] = ConocimientoInformatico.objects.get(pk=request.GET['id'])
                    return render(request, "alu_hojavida/delconocimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'addconocimiento':
                try:
                    data['title'] = u'Adicionar Conocimiento'
                    data['form'] = ConocimientoInformaticoForm()
                    return render(request, "alu_hojavida/addconocimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'addconocimientoadicional':
                try:
                    data['title'] = 'Adicionar otro conocimiento'
                    data['form'] = ConocimientoForm()
                    return render(request, "alu_hojavida/addconocimientoadicional.html", data)
                except Exception as ex:
                    pass

            if action == 'editconocimiento':
                try:
                    data['title'] = u'Editar Conocimiento'
                    data['conocimiento'] = conocimiento = ConocimientoInformatico.objects.get(pk=request.GET['id'])
                    data['form'] = ConocimientoInformaticoForm(initial={'herramienta': conocimiento.herramienta,
                                                                        'descripcion': conocimiento.descripcion,
                                                                        'nivel': conocimiento.nivel})
                    return render(request, "alu_hojavida/editconocimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'delconocimientoadicional':
                try:
                    data['title'] = u'Borrar conocimiento adicional'
                    data['conocimiento'] = ConocimientoAdiconal.objects.get(pk=request.GET['id'])
                    return render(request, "alu_hojavida/delconocimientoadicional.html", data)
                except Exception as ex:
                    pass

            if action == 'editconocimientoadicional':
                try:
                    data['title'] = u'Editar Conocimiento'
                    data['conocimiento'] = conocimiento = persona.conocimientoinformatico_set.get(pk=request.GET['id'])
                    data['form'] = ConocimientoForm(initial={'nombre': conocimiento.nombre,
                                                             'descripcion': conocimiento.descripcion})
                    return render(request, "alu_hojavida/editconocimientoadicional.html", data)
                except Exception as ex:
                    pass

            if action == 'editexperiencia':
                try:
                    data['title'] = u'Editar Experiencia Laboral'
                    data['experiencia'] = experiencia = SeguimientoEstudiante.objects.get(pk=request.GET['id'])
                    data['form'] = SeguimientoEstudianteForm(initial={'empresa': experiencia.empresa,
                                                                      'industria': experiencia.industria,
                                                                      'cargo': experiencia.cargo,
                                                                      'ocupacion': experiencia.ocupacion,
                                                                      'responsabilidades': experiencia.responsabilidades,
                                                                      'telefono': experiencia.telefono,
                                                                      'email': experiencia.email,
                                                                      'sueldo': experiencia.sueldo,
                                                                      'ejerce': experiencia.ejerce,
                                                                      'labora': False if experiencia.fechafin else True,
                                                                      'fecha': experiencia.fecha,
                                                                      'fechafin': experiencia.fechafin})
                    return render(request, "alu_hojavida/editexperiencia.html", data)
                except Exception as ex:
                    pass

            if action == 'delestudio':
                try:
                    data['title'] = u'Eliminar estudios realizados'
                    data['estudio'] = EstudioInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "alu_hojavida/delestudio.html", data)
                except Exception as ex:
                    pass

            if action == 'delreferencia':
                try:
                    data['title'] = u'Eliminar referencia'
                    data['referencia'] = ReferenciaPersona.objects.get(pk=request.GET['id'])
                    return render(request, "alu_hojavida/delreferencia.html", data)
                except Exception as ex:
                    pass

            if action == 'editestudio':
                try:
                    data['title'] = u'Editar Estudios'
                    data['estudio'] = estudio = EstudioInscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = EstudioInscripcionSuperiorForm(initial={'incorporacion': estudio.incorporacion,
                                                                           'superiores': estudio.universidad,
                                                                           'carrera': estudio.carrera,
                                                                           'titulo': estudio.titulo,
                                                                           'anoestudio': estudio.anoestudio,
                                                                           'posteriores': estudio.estudiosposteriores,
                                                                           'graduado': estudio.graduado})
                    return render(request, "alu_hojavida/editestudio.html", data)
                except Exception as ex:
                    pass

            if action == 'editreferencia':
                try:
                    data['title'] = u'Editar Referencia'
                    data['referencia'] = referencia = ReferenciaPersona.objects.get(pk=request.GET['id'])
                    data['form'] = ReferenciaPersonaForm(initial={'nombres': referencia.nombres,
                                                                  'apellidos': referencia.apellidos,
                                                                  'email': referencia.email,
                                                                  'telefono': referencia.telefono,
                                                                  'institucion': referencia.institucion,
                                                                  'relacion': referencia.relacion})
                    return render(request, "alu_hojavida/editreferencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addestudio':
                try:
                    data['title'] = u'Adicionar estudios superiores'
                    data['form'] = EstudioInscripcionSuperiorForm(initial={'incorporacion': datetime.now().date().year,
                                                                           'anoestudio': 0,
                                                                           'posteriores': True,
                                                                           'graduado': True})
                    return render(request, "alu_hojavida/addestudio.html", data)
                except Exception as ex:
                    pass

            if action == 'addreferencia':
                try:
                    data['title'] = u'Adicionar referencia'
                    data['form'] = ReferenciaPersonaForm()
                    return render(request, "alu_hojavida/addreferencia.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u"Hoja de vida del estudiante"
            data['persona'] = persona = request.session['persona']
            data['experiencias'] = data['persona'].tiene_experiencia()
            data['estudios'] = data['persona'].tiene_estudios()
            data['idiomas'] = data['persona'].tiene_idiomadomina()
            data['conocimientosadicionales'] = data['persona'].tiene_conocimientosadicionales()
            data['conocimientos'] = data['persona'].tiene_conocimientos()
            data['nivel'] = NIVEL_CONOCIMIENTO
            data['referencias'] = data['persona'].tiene_referencias()
            data['reporte_0'] = obtener_reporte('hoja_vida')
            co = []
            for conocimiento in persona.conocimientoinformatico_set.all():
                if conocimiento.herramienta.categoria.id not in co:
                    co.append(conocimiento.herramienta.categoria.id)
            data['categoriaherramienta'] = CategoriaHerramienta.objects.filter(id__in=co)
            return render(request, 'alu_hojavida/hojavida.html', data)