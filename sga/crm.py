# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import CALLCENTER_CONTACTO, EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.forms import PreInscritoForm, SeguimientoPreInscritoForm, \
    CampannaCaptacionForm, CampannaDifusionForm, CampannaDifusionSendForm
from sga.funciones import MiPaginador, log, formato24h, generar_nombre
from sga.models import Inscripcion, PreInscrito, SeguimientoPreInscrito, CampannaCaptacion, \
    CampannaDifusion, miinstitucion, Persona
from sga.tasks import send_html_mail
unicode = str

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = PreInscritoForm(request.POST)
                if f.is_valid():
                    if PreInscrito.objects.values('id').filter(cedula=f.cleaned_data['cedula']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El numero de cedula ingresado esta registrado a una pre inscripcion."})
                    if Persona.objects.values('id').filter(cedula=f.cleaned_data['cedula']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El numero de cedula ingresado esta registrado a un usuario."})
                    preinscrito = PreInscrito(fecha=datetime.now().date(),
                                              nombres=f.cleaned_data['nombres'],
                                              apellido1=f.cleaned_data['apellido1'],
                                              apellido2=f.cleaned_data['apellido2'],
                                              sexo=f.cleaned_data['sexo'],
                                              cedula=f.cleaned_data['cedula'],
                                              telefono_celular=f.cleaned_data['telefono_celular'],
                                              telefono_domicilio=f.cleaned_data['telefono_domicilio'],
                                              telefono_trabajo=f.cleaned_data['telefono_trabajo'],
                                              email=f.cleaned_data['email'],
                                              institucion=f.cleaned_data['institucion'],
                                              pre=f.cleaned_data['pre'],
                                              carrera=f.cleaned_data['carrera'],
                                              direccion=f.cleaned_data['direccion'],
                                              ref_direccion=f.cleaned_data['ref_direccion'],
                                              comoseinformo=f.cleaned_data['comoseinformo'],
                                              presencial=f.cleaned_data['presencial'],
                                              observacion=f.cleaned_data['observacion'],
                                              registro=request.session['persona'])
                    if 'comoseinformootras' in request.POST:
                        preinscrito.comoseinformootro = f.cleaned_data['comoseinformootras']
                    preinscrito.save(request)
                    log(u'Adiciono pre inscrito: %s' % preinscrito, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                preinscrito = PreInscrito.objects.get(pk=request.POST['id'])
                f = PreInscritoForm(request.POST)
                if f.is_valid():
                    preinscrito.nombres = f.cleaned_data['nombres']
                    preinscrito.apellido1 = f.cleaned_data['apellido1']
                    preinscrito.apellido2 = f.cleaned_data['apellido2']
                    preinscrito.sexo = f.cleaned_data['sexo']
                    preinscrito.telefono_celular = f.cleaned_data['telefono_celular']
                    preinscrito.telefono_domicilio = f.cleaned_data['telefono_domicilio']
                    preinscrito.telefono_trabajo = f.cleaned_data['telefono_trabajo']
                    preinscrito.email = f.cleaned_data['email']
                    preinscrito.institucion = f.cleaned_data['institucion']
                    preinscrito.pre = f.cleaned_data['pre']
                    preinscrito.carrera = f.cleaned_data['carrera']
                    preinscrito.direccion = f.cleaned_data['direccion']
                    preinscrito.ref_direccion = f.cleaned_data['ref_direccion']
                    preinscrito.comoseinformo = f.cleaned_data['comoseinformo']
                    preinscrito.comoseinformootro = f.cleaned_data['comoseinformootras']
                    preinscrito.edito = request.session['persona']
                    preinscrito.save(request)
                    log(u'Modifico pre inscrito: %s' % preinscrito, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addseguimiento':
            try:
                preinscrito = PreInscrito.objects.get(pk=request.POST['id'])
                f = SeguimientoPreInscritoForm(request.POST)
                if f.is_valid():
                    hora = formato24h(f.cleaned_data['proximahora'])
                    seguimiento = SeguimientoPreInscrito(preinscrito=preinscrito,
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         usuario=request.session['persona'].usuario,
                                                         estado=f.cleaned_data['estado'],
                                                         observacion=f.cleaned_data['observacion'])
                    if 'observacionotra' in request.POST:
                        seguimiento.observacionotra = f.cleaned_data['observacionotra']
                    seguimiento.save(request)
                    if f.cleaned_data['agendar']:
                        preinscrito.proxima_fecha = f.cleaned_data['proximafecha']
                        preinscrito.proxima_hora = hora
                        preinscrito.save(request)
                    else:
                        preinscrito.proxima_fecha = None
                        preinscrito.proxima_hora = None
                        preinscrito.save(request)
                    log(u'Adiciono seguimiento de pre inscrito: %s' % seguimiento.preinscrito, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcampanna':
                try:
                    f = CampannaCaptacionForm(request.POST)
                    if f.is_valid():
                        campanna = CampannaCaptacion(nombre=f.cleaned_data['nombre'],
                                                     fecha_fin=f.cleaned_data['fecha_fin'])
                        campanna.save(request)
                        log(u'Adiciono campaña de captacion: %s' % campanna, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcampanna':
                try:
                    f = CampannaCaptacionForm(request.POST)
                    campanna = CampannaCaptacion.objects.get(pk=request.POST['id'])
                    if f.is_valid():
                        campanna.nombre = f.cleaned_data['nombre']
                        campanna.fecha_fin = f.cleaned_data['fecha_fin']
                        campanna.save(request)
                        log(u'Modifico campaña de difusion: %s' % campanna, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddifusion':
                try:
                    f = CampannaDifusionForm(request.POST, request.FILES)
                    campanna = CampannaCaptacion.objects.get(pk=request.POST['id'])
                    if f.is_valid():
                        newfile = request.FILES['claqueta']
                        newfile._name = generar_nombre("claqueta_", newfile._name)
                        difusion = CampannaDifusion(campanna=campanna,
                                                    titulo=f.cleaned_data['titulo'],
                                                    contenido=f.cleaned_data['contenido'],
                                                    link=f.cleaned_data['link'],
                                                    claqueta=newfile,
                                                    enviado=False,
                                                    fecha=datetime.now().date())
                        difusion.save(request)
                        log(u'Adiciono campaña de difusion: %s' % difusion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editdifusion':
                try:
                    f = CampannaDifusionForm(request.POST, request.FILES)
                    difusion = CampannaDifusion.objects.get(pk=request.POST['id'])
                    if f.is_valid():
                        newfile = request.FILES['claqueta']
                        newfile._name = generar_nombre("claqueta_", newfile._name)
                        difusion.titulo = f.cleaned_data['titulo']
                        difusion.contenido = f.cleaned_data['contenido']
                        difusion.link = f.cleaned_data['link']
                        difusion.claqueta = newfile
                        difusion.fecha = datetime.now().date()
                        difusion.save(request)
                        log(u'Adiciono difusion: %s' % difusion, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verdifusion':
            try:
                difusion = CampannaDifusion.objects.get(pk=request.POST['id'])
                return JsonResponse({'result': 'ok', 'titulo': difusion.titulo, 'campanna': unicode(difusion.campanna), 'contenido': difusion.contenido, 'claqueta': difusion.claqueta.url})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u'Error al obtener los datos'})

        elif action == 'buscarpreinscripcion':
            try:
                if PreInscrito.objects.values('id').filter(cedula=request.POST['ced']).exists():
                    preinscrito = PreInscrito.objects.filter(cedula=request.POST['ced'])[0]
                    return JsonResponse({'result': 'ok', 'preinscrito': unicode(preinscrito), 'preinscrito_id': preinscrito.id})
                else:
                    return JsonResponse({'result': 'bad'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u'Error al obtener los datos'})

        elif action == 'senddifusion_registrados':
            try:
                f = CampannaDifusionSendForm(request.POST)
                campanna = CampannaDifusion.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    if not f.cleaned_data['inscritos'] and not f.cleaned_data['preinscritos']:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Debe seleccionar inscritos y/o pre inscritos'})
                    lista_carreras = []
                    for carrera in f.cleaned_data['carreras']:
                        lista_carreras.append(carrera.id)
                    lista_envio = []
                    if f.cleaned_data['inscritos']:
                        if lista_carreras:
                            for inscrito in Inscripcion.objects.filter(carrera__in=lista_carreras):
                                if inscrito.persona.email:
                                    lista_envio.append(inscrito.persona.email)
                        else:
                            for inscrito in Inscripcion.objects.all():
                                if inscrito.persona.email:
                                    lista_envio.append(inscrito.persona.email)
                    if f.cleaned_data['preinscritos']:
                        if lista_carreras:
                            for preinscrito in PreInscrito.objects.filter(carrera__in=lista_carreras, inscripcion=None):
                                if preinscrito.email:
                                    lista_envio.append(preinscrito.email)
                        else:
                            for preinscrito in PreInscrito.objects.filter(inscripcion=None):
                                if preinscrito.email:
                                    lista_envio.append(preinscrito.email)
                    if not lista_envio:
                        return JsonResponse({'result': 'bad', 'mensaje': u'No existen destinatorios para el envío del email'})
                    send_html_mail(unicode(campanna.titulo), "emails/enviocampanna.html", {'campanna': campanna, 'location': request.POST['location'], 't': miinstitucion(), 'contacto': CALLCENTER_CONTACTO, 'dominio': EMAIL_DOMAIN}, lista_envio, [])
                    campanna.enviado = True
                    campanna.fecha_difusion = datetime.now().date()
                    campanna.save(request)
                    log(u'Envío de campaña: %s' % campanna, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al enviar el email'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar interesado'
                    data['form'] = PreInscritoForm(initial={'pre': True,
                                                            'presencial': True})
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "crm/add.html", data)
                except Exception as ex:
                    pass

            if action == 'seguimiento':
                try:
                    data['title'] = u'Seguimiento al interesado'
                    data['preinscrito'] = preinscrito = PreInscrito.objects.get(pk=request.GET['id'])
                    data['seguimientos'] = SeguimientoPreInscrito.objects.filter(preinscrito=preinscrito).order_by('-fecha', '-hora')
                    return render(request, "crm/seguimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'addseguimiento':
                try:
                    data['title'] = u'Registrar observación de seguimiento'
                    preinscrito = PreInscrito.objects.get(pk=request.GET['id'])
                    data['preinscripcion'] = preinscrito
                    data['form'] = SeguimientoPreInscritoForm(initial={'proximafecha': datetime.now().date(),
                                                                       'proximahora': '12:00 PM'})
                    return render(request, "crm/addseguimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar interesado'
                    preinscrito = PreInscrito.objects.get(pk=request.GET['id'])
                    data['preinscrito'] = preinscrito
                    form = PreInscritoForm(initial={'nombres': preinscrito.nombres,
                                                    'apellido1': preinscrito.apellido1,
                                                    'apellido2': preinscrito.apellido2,
                                                    'sexo': preinscrito.sexo,
                                                    'cedula': preinscrito.cedula,
                                                    'telefono_celular': preinscrito.telefono_celular,
                                                    'telefono_domicilio': preinscrito.telefono_domicilio,
                                                    'telefono_trabajo': preinscrito.telefono_trabajo,
                                                    'email': preinscrito.email,
                                                    'institucion': preinscrito.institucion,
                                                    'pre': preinscrito.pre,
                                                    'carrera': preinscrito.carrera,
                                                    'direccion': preinscrito.direccion,
                                                    'ref_direccion': preinscrito.ref_direccion,
                                                    'comoseinformo': preinscrito.comoseinformo,
                                                    'comoseinformootras': preinscrito.comoseinformootro,
                                                    'observacion': preinscrito.observacion})
                    form.editar()
                    data['form'] = form
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "crm/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'agenda':
                try:
                    data['title'] = u'Llamadas por realizar'
                    data['preinscritos'] = PreInscrito.objects.filter(proxima_fecha__lte=datetime.now().date())
                    return render(request, "crm/agenda.html", data)
                except Exception as ex:
                    pass

            elif action == 'campannas':
                try:
                    data['title'] = u'Campañas para captación de estudiantes'
                    data['campannas'] = CampannaCaptacion.objects.all()
                    return render(request, "crm/campannas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcampanna':
                try:
                    data['title'] = u'Nueva campaña para captación de estudiantes'
                    form = CampannaCaptacionForm(initial={'fecha_fin': datetime.now().date()})
                    data['form'] = form
                    return render(request, "crm/addcampanna.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcampanna':
                try:
                    data['title'] = u'Editar campaña'
                    campanna = CampannaCaptacion.objects.get(pk=request.GET['id'])
                    form = CampannaCaptacionForm(initial={'nombre': campanna.nombre,
                                                          'fecha_fin': campanna.fecha_fin})
                    data['campanna'] = campanna
                    data['form'] = form
                    return render(request, "crm/editcampanna.html", data)
                except Exception as ex:
                    pass

            elif action == 'difundir':
                try:
                    data['title'] = u'Difusiones de campaña'
                    campanna = CampannaCaptacion.objects.get(pk=request.GET['id'])
                    difusiones = CampannaDifusion.objects.filter(campanna=campanna)
                    data['difusiones'] = difusiones
                    data['campanna'] = campanna
                    return render(request, "crm/difundir.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddifusion':
                try:
                    data['title'] = u'Crear difusión'
                    campanna = CampannaCaptacion.objects.get(pk=request.GET['id'])
                    form = CampannaDifusionForm()
                    data['campanna'] = campanna
                    data['form'] = form
                    return render(request, "crm/adddifusion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdifusion':
                try:
                    data['title'] = u'Editar difusión'
                    difusion = CampannaDifusion.objects.get(pk=request.GET['id'])
                    form = CampannaDifusionForm(initial={'titulo': difusion.titulo,
                                                         'link': difusion.link,
                                                         'contenido': difusion.contenido})
                    data['difusion'] = difusion
                    data['form'] = form
                    return render(request, "crm/editdifusion.html", data)
                except Exception as ex:
                    pass

            elif action == 'senddifusion_registrados':
                try:
                    data['title'] = u'Envío de campañas'
                    difusion = CampannaDifusion.objects.get(pk=request.GET['id'])
                    data['difusion'] = difusion
                    form = CampannaDifusionSendForm()
                    data['form'] = form
                    return render(request, "crm/envio_difusion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de Interesados'
            search = None
            ids = None
            preinscritos = PreInscrito.objects.filter(inscripcion=None).order_by('fecha')
            if 'id' in request.GET:
                ids = request.GET['id']
                preinscritos = PreInscrito.objects.filter(id=ids)
            elif 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    preinscritos = PreInscrito.objects.filter(Q(nombres__icontains=search) |
                                                              Q(apellido1__icontains=search) |
                                                              Q(apellido2__icontains=search) |
                                                              Q(cedula__icontains=search)).order_by('fecha')
                else:
                    preinscritos = PreInscrito.objects.filter(Q(apellido1__icontains=ss[0]) &
                                                              Q(apellido2__icontains=ss[1])).order_by('fecha')
            paging = MiPaginador(preinscritos, 25)
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
            data['preinscritos'] = page.object_list
            data['llamadaspendientes'] = PreInscrito.objects.values('id').filter(proxima_fecha__lte=datetime.now().date()).exists()
            return render(request, "crm/view.html", data)