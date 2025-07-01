# -*- coding: latin-1 -*-
import string
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import last_access
from settings import DEFAULT_PASSWORD, EMPLEADORES_GRUPO_ID, AUTOREGISTRO_EMPRESA, EMAIL_DOMAIN, AUTOREGISTRO_EMPRESA_AUTORIZAR, SEXO_FEMENINO
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import OfertaLaboralBolsaForm, AgendarCitaForm, CambioClaveForm, RetroalimentacionOfertaForm
from sga.funciones import tituloinstitucion, MiPaginador, log, variable_valor
from sga.models import Persona, EmpresaEmpleadora, Empleador, OfertaLaboral, AplicanteOferta, miinstitucion, \
    NIVEL_CONOCIMIENTO, ConocimientoInformatico, CategoriaHerramienta, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    persona = None
    if "persona" in request.session:
        persona = request.session['persona']
        if not persona.mi_empresa():
            return HttpResponseRedirect("/")
        adduserdata(request, data)
        persona = data['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'verdescripcion':
                try:
                    oferta = OfertaLaboral.objects.get(pk=request.POST['id'])
                    return JsonResponse({'result': 'ok', 'area': oferta.area.descripcion, 'cargo': oferta.cargo, 'descripcion': oferta.descripcion})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u'Error al obtener los datos'})

            if action == 'changepass':
                try:
                    f = CambioClaveForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['nueva'] == DEFAULT_PASSWORD:
                            return JsonResponse({"result": "bad", "mensaje": u"Clave no puede ser igual a clave por defecto."})
                        persona = request.session['persona']
                        usuario = persona.usuario
                        if usuario.check_password(f.cleaned_data['anterior']):
                            usuario.set_password(f.cleaned_data['nueva'])
                            usuario.save(request)
                            persona.clave_cambiada()
                            log(u"Cambio de contaseña: %s" % persona, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Clave anterior no coincide con la registrada."})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cambiar clave."})

            if action == 'asigcita':
                try:
                    registrado = AplicanteOferta.objects.get(pk=request.POST['id'])
                    f = AgendarCitaForm(request.POST)
                    if f.is_valid():
                        registrado.fechaentrevista = f.cleaned_data['fechaentrevista']
                        registrado.horaentrevista = f.cleaned_data['horaentrevista']
                        registrado.lugar = f.cleaned_data['lugar']
                        registrado.personacontacto = f.cleaned_data['personacontacto']
                        registrado.telefonocontacto = f.cleaned_data['telefonocontacto']
                        registrado.citaconfirmada = False
                        registrado.save(request)
                        log(u"Asignar cita para oferta laboral aplicada: %s [%s]" % (registrado,registrado.id), request, "edit")
                        send_html_mail("Cita para oferta laboral aplicada", "emails/nuevacita.html", {'sistema': request.session['nombresistema'], 'registro': registrado, 't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, registrado.inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'login':
                try:
                    user = authenticate(username=(request.POST['user']).lower(), password=request.POST['pass'])
                    if not user:
                        return JsonResponse({"result": "bad", "mensaje": u"Usuario no registrado o clave incorrecta."})
                    if not user.is_active:
                        return JsonResponse({"result": "bad", "mensaje": u"Su empresa no esta activa."})
                    else:
                        if Persona.objects.filter(usuario=user).exists():
                            persona = Persona.objects.filter(usuario=user)[0]
                            if not persona.es_empleador():
                                return JsonResponse({"result": "bad", "mensaje": u"Este usuario no es empleador."})
                            request.session['login_manual'] = True
                            login(request, user)
                            request.session['perfilprincipal'] = persona.perfilusuario_principal(persona.mi_perfil(), 'sga')
                            request.session['persona'] = persona
                            request.session['nombresistema'] = u'Sistema de Gestión Academica'
                            request.session['tiposistema'] = 'sga'
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"No existe usuario registrado a esta empresa."})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error del sistema."})

            if action == 'del':
                try:
                    oferta = OfertaLaboral.objects.get(pk=request.POST['id'])
                    if oferta.aplicanteoferta_set.exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Existen aplicaciones a esta oferta."})
                    log(u"Elimino oferta laboral: %s" % oferta, request, "del")
                    oferta.delete()
                    return JsonResponse({"result": "ok", "id": oferta.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'edit':
                try:
                    oferta = OfertaLaboral.objects.get(pk=request.POST['id'])
                    f = OfertaLaboralBolsaForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['fin'] < f.cleaned_data['inicio']:
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
                        oferta.inicio = f.cleaned_data['inicio']
                        oferta.fin = f.cleaned_data['fin']
                        oferta.cargo = f.cleaned_data['cargo']
                        oferta.descripcion = f.cleaned_data['descripcion']
                        oferta.area = f.cleaned_data['area']
                        oferta.tiempo = f.cleaned_data['tiempo']
                        oferta.salario = f.cleaned_data['salario']
                        oferta.lugar = f.cleaned_data['lugar']
                        oferta.sexo = f.cleaned_data['sexo']
                        oferta.plazas = f.cleaned_data['plazas']
                        # oferta.carreras = f.cleaned_data['carreras']
                        oferta.canton = f.cleaned_data['canton']
                        oferta.save(request)
                        log(u"Modifico oferta laboral: %s" % oferta, request, "edit")
                        return JsonResponse({"result": "ok", "id": oferta.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'retroalimentacion':
                try:
                    oferta = OfertaLaboral.objects.get(pk=request.POST['id'])
                    f = RetroalimentacionOfertaForm(request.POST)
                    if f.is_valid():
                        oferta.retroalimentacion = f.cleaned_data['retroalimentacion']
                        oferta.save(request)
                        log(u"Ingreso Retroalimentacion oferta laboral: %s" % oferta, request, "edit")
                        return JsonResponse({"result": "ok", "id": oferta.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'add':
                try:
                    persona = request.session['persona']
                    f = OfertaLaboralBolsaForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['fin'] < datetime.now().date() or f.cleaned_data['fin'] < f.cleaned_data['inicio']:
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
                        oferta = OfertaLaboral(empresa=persona.mi_empresa(),
                                               registro=datetime.now().date(),
                                               inicio=f.cleaned_data['inicio'],
                                               fin=f.cleaned_data['fin'],
                                               cerrada=True,
                                               cargo=f.cleaned_data['cargo'],
                                               descripcion=f.cleaned_data['descripcion'],
                                               area=f.cleaned_data['area'],
                                               tiempo=f.cleaned_data['tiempo'],
                                               salario=f.cleaned_data['salario'],
                                               lugar=f.cleaned_data['lugar'],
                                               sexo=f.cleaned_data['sexo'],
                                               plazas=f.cleaned_data['plazas'],
                                               canton=f.cleaned_data['canton'],
                                               visibleinscrito=2)
                        oferta.save(request)
                        # oferta.carreras = f.cleaned_data['carreras']
                        log(u'Adiciono oferta laboral: %s' % oferta, request, "add")
                        return JsonResponse({"result": "ok", "id": oferta.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'registro':
                try:
                    ruc = request.POST['ruc']
                    if EmpresaEmpleadora.objects.filter(ruc=ruc, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Empresa ya registrada."})
                    else:
                        empresa = EmpresaEmpleadora(nombre=request.POST['empresa'],
                                                    ruc=ruc,
                                                    direccion=request.POST['direccion'],
                                                    telefonos=request.POST['telefono'],
                                                    autorizada=False if AUTOREGISTRO_EMPRESA_AUTORIZAR else True)
                        empresa.save(request)
                        apellidos = request.POST['responsable_apellidos']
                        apellido1 = ""
                        apellido2 = ""
                        if apellidos.split().__len__() == 1:
                            apellido1 = apellidos
                            apellido2 = ""
                        elif apellidos.split().__len__() == 2:
                            apellido1 = apellidos.split()[0]
                            apellido2 = apellidos.split()[1]
                        elif apellidos.split().__len__() >= 3:
                            apellido1 = ""
                            for x in apellidos.split()[:apellidos.split().__len__() - 1]:
                                apellido1 += x + ' '
                            apellido2 = apellidos.split()[apellidos.split().__len__() - 1]
                        persona = Persona(nombres=request.POST['responsable_nombre'],
                                          apellido1=apellido1,
                                          apellido2=apellido2,
                                          email=request.POST['email'],
                                          nacimiento=datetime.now().date(),
                                          sexo_id=SEXO_FEMENINO)
                        persona.save(request)
                        username = ruc
                        password = DEFAULT_PASSWORD
                        user = User.objects.create_user(username, "", password)
                        user.save()
                        persona.usuario = user
                        persona.save(request)
                        grupo = Group.objects.get(pk=EMPLEADORES_GRUPO_ID)
                        grupo.user_set.add(user)
                        grupo.save()
                        empleador = Empleador(empresa=empresa,
                                              persona=persona,
                                              cargo=request.POST['responsable_cargo'])
                        empleador.save(request)
                        persona.crear_perfil(empleador=empleador)
                        log(u"Registro nuevo empleador: %s" % empleador, request, "add", user=user)
                        send_html_mail("Registro a bolsa laboral", "emails/nuevoregistro.html", {'sistema': 'Sistema de gestion', 'e': empleador, 'clave': DEFAULT_PASSWORD, 'autorizar': AUTOREGISTRO_EMPRESA_AUTORIZAR, 't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, empleador.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al registrarse."})

            if action == 'confirmar':
                try:
                    aplicanteoferta = AplicanteOferta.objects.get(pk=request.POST['id'], status=True)
                    aplicanteoferta.citaconfirmada = True
                    aplicanteoferta.save(request)
                    log(u'Confirmo cita Oferta: %s' % aplicanteoferta, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al confirmar los datos."})

            if action == 'aprobar':
                try:
                    aplicanteoferta = AplicanteOferta.objects.get(pk=request.POST['id'], status=True)
                    aplicanteoferta.aprobada = True
                    aplicanteoferta.save(request)
                    log(u'Aprobo Oferta Laboral: %s' % aplicanteoferta, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verhojavida':
                try:
                    data['title'] = u"Hoja de vida del aplicante"
                    data['aplicante'] = AplicanteOferta.objects.get(pk=request.GET['id'])
                    data['experiencias'] = data['aplicante'].inscripcion.persona.tiene_experiencia()
                    data['estudios'] = data['aplicante'].inscripcion.persona.tiene_estudios()
                    data['idiomas'] = data['aplicante'].inscripcion.persona.tiene_idiomadomina()
                    data['conocimientos'] = data['aplicante'].inscripcion.persona.tiene_conocimientos()
                    data['conocimientosadicionales'] = data['aplicante'].inscripcion.persona.tiene_conocimientosadicionales()
                    data['referencias'] = data['aplicante'].inscripcion.persona.tiene_referencias()
                    data['nivel'] = NIVEL_CONOCIMIENTO
                    data['categoriaherramienta'] = []
                    if ConocimientoInformatico.objects.filter(persona=data['aplicante'].inscripcion.persona).exists():
                        co = []
                        conocimientocategoria = ConocimientoInformatico.objects.filter(persona=data['aplicante'].inscripcion.persona)
                        for cono in conocimientocategoria:
                            if cono.herramienta.categoria.id not in co:
                                co.append(cono.herramienta.categoria.id)
                        data['categoriaherramienta'] = CategoriaHerramienta.objects.filter(id__in=co)
                    return render(request, "bolsalaboral/hojavida.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrar':
                try:
                    oferta = OfertaLaboral.objects.get(pk=request.GET['id'])
                    oferta.cerrada = True
                    oferta.save(request)
                    return HttpResponseRedirect("/bolsalaboral?id=" + request.GET['id'])
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'abrir':
                try:
                    oferta = OfertaLaboral.objects.get(pk=request.GET['id'])
                    oferta.cerrada = False
                    if not oferta.fin >= datetime.now().date():
                        oferta.fin = datetime.now().date()
                    oferta.save(request)
                    return HttpResponseRedirect("/bolsalaboral?id=" + request.GET['id'])
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'changepass':
                try:
                    data['title'] = u'Cambio de clave'
                    data['form'] = CambioClaveForm()
                    data['cambio_clave'] = persona.necesita_cambiar_clave()
                    return render(request, "empleadorchangepassbs.html", data)
                except Exception as ex:
                    pass

            if action == 'asigcita':
                try:
                    data['title'] = u"Asignar cita"
                    registrado = AplicanteOferta.objects.get(pk=request.GET['id'])
                    data['form'] = form = AgendarCitaForm(initial={"horaentrevista": registrado.horaentrevista.__str__() if registrado.horaentrevista else "12:00",
                                                                   "fechaentrevista": registrado.fechaentrevista if registrado.fechaentrevista else datetime.now().date(),
                                                                   "lugar": registrado.lugar if registrado.lugar else registrado.oferta.empresa.direccion,
                                                                   "personacontacto": registrado.personacontacto if registrado.personacontacto else data['persona'],
                                                                   "telefonocontacto": registrado.telefonocontacto if registrado.telefonocontacto else registrado.oferta.empresa.telefonos})
                    data['registrado'] = registrado

                    return render(request, "bolsalaboral/asigcita.html", data)
                except Exception as ex:
                    pass

            if action == 'registrados':
                try:
                    data['title'] = u"Lista de registrados"
                    oferta = OfertaLaboral.objects.get(pk=request.GET['id'])
                    if oferta.visibleinscrito==1:
                        data['registrados'] = oferta.aplicanteoferta_set.filter(status=True, estado=True).order_by('inscripcion__persona__nombres')
                    else:
                        data['registrados'] = oferta.aplicanteoferta_set.filter(validada=True, status=True, estado=True).order_by('inscripcion__persona__nombres')
                    data['reporte_0'] = obtener_reporte('hoja_vida_sagest')
                    return render(request, "bolsalaboral/registrados.html", data)
                except Exception as ex:
                    pass

            if action == "del":
                try:
                    data['title'] = u"Eliminar oferta laboral"
                    data['oferta'] = oferta = OfertaLaboral.objects.get(pk=request.GET['id'])
                    return render(request, "bolsalaboral/del.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u"Nueva oferta laboral"
                    form = OfertaLaboralBolsaForm(initial={"inicio": datetime.now().date(),
                                                           "fin": (datetime.now() + timedelta(days=30)).date()})
                    form.sin_empleador()
                    data['form'] = form
                    return render(request, "bolsalaboral/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u"Editar oferta laboral"
                    data['oferta'] = oferta = OfertaLaboral.objects.get(pk=request.GET['id'])
                    form = OfertaLaboralBolsaForm(initial={"inicio": oferta.inicio,
                                                      "fin": oferta.fin,
                                                      "cargo": oferta.cargo,
                                                      "descripcion": oferta.descripcion,
                                                      "area": oferta.area,
                                                      "tiempo": oferta.tiempo,
                                                      "salario": oferta.salario,
                                                      "lugar": oferta.lugar,
                                                      "sexo": oferta.sexo,
                                                      "carreras": oferta.carreras.all(),
                                                      "plazas": oferta.plazas,
                                                      "canton": oferta.canton})
                    form.sin_empleador()
                    data['form'] = form
                    return render(request, "bolsalaboral/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'retroalimentacion':
                try:
                    data['title'] = u"Retroalimentación oferta laboral"
                    data['oferta'] = oferta = OfertaLaboral.objects.get(pk=request.GET['id'])
                    form = RetroalimentacionOfertaForm(initial={"retroalimentacion": oferta.retroalimentacion})
                    data['form'] = form
                    return render(request, "bolsalaboral/retroalimentacion.html", data)
                except Exception as ex:
                    pass

            if action == 'confirmar':
                try:
                    data['title'] = u'Confirmar Cita'
                    data['aplicanteoferta'] = AplicanteOferta.objects.get(pk=request.GET['id'])
                    return render(request, "bolsalaboral/confirmar.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobar':
                try:
                    data['title'] = u'Aprobar'
                    data['aplicanteoferta'] = AplicanteOferta.objects.get(pk=request.GET['id'])
                    return render(request, "bolsalaboral/aprobar.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            if 'persona' in request.session:
                persona = request.session['persona']
                data['title'] = u'Listado de ofertas laborales'
                if not persona.es_empleador():
                    HttpResponseRedirect("/")
                empresa = persona.mi_empresa()
                data['empresa'] = empresa
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                    ofertas = empresa.ofertalaboral_set.filter(Q(cargo__icontains=search) |
                                                               Q(descripcion__icontains=search) |
                                                               Q(area__icontains=search))
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    ofertas = empresa.ofertalaboral_set.filter(id=ids)
                else:
                    ofertas = empresa.ofertalaboral_set.all()
                paging = MiPaginador(ofertas, 25)
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
                data['ofertas'] = page.object_list
                data['autorizacion'] = AUTOREGISTRO_EMPRESA_AUTORIZAR
                return render(request, "bolsalaboral/panel.html", data)
            else:
                data = {"title": "Login", "background": 7, 'request': request}
                tituloinst = tituloinstitucion()
                data['institucion'] = tituloinst.nombre
                data['mail'] = tituloinst.correo
                data['autoregistro'] = AUTOREGISTRO_EMPRESA
                return render(request, "bolsalaboral/login.html", data)