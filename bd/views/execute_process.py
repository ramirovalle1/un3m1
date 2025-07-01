from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import get_template

from bd.forms import ProcesoPythonForm
from bd.models import PythonProcess
from decorators import last_access, secure_module
from sga.commonviews import adduserdata, traerNotificaciones
from sga.excelbackground import ejecutar_procesos_background
from sga.funciones import log, generar_nombre
from sga.models import Notificacion
from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    lista_usuarios_permitidos = [43766, 29882, 31352, 35269]
    if not request.user.id in lista_usuarios_permitidos:
        return HttpResponseRedirect("/?info=No tiene acceso a este módulo.")
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    data['lista_usuarios_permitidos'] = lista_usuarios_permitidos
    if 'action' in request.POST:
        action = request.POST['action']

        if action == 'add':
            try:
                f = ProcesoPythonForm(request.POST)
                if not f.is_valid():
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': False, "form": form_error, "mensaje": "Error en el formulario"})
                PythonProcess_n = PythonProcess(nombre=f.cleaned_data['nombre'],
                                              descripcion=f.cleaned_data['descripcion'],
                                               tipo=f.cleaned_data['tipo'], code=f.cleaned_data['code'])
                if 'anexo' in request.FILES:
                    nfileDocumento = request.FILES['anexo']
                    extensionDocumento = nfileDocumento._name.split('.')
                    tamDocumento = len(extensionDocumento)
                    exteDocumento = extensionDocumento[tamDocumento - 1]
                    if nfileDocumento.size > 26214400:
                        raise NameError(u"Error al cargar, el archivo es mayor a 25 Mb.")
                    if not exteDocumento.lower() in ['xls', 'xlsx']:
                        raise NameError(u"Error al cargar, solo se permiten archivos .xls, .xlsx")
                    nfileDocumento._name = generar_nombre("anexo_proceso", nfileDocumento._name)

                    PythonProcess_n.anexo = nfileDocumento
                if 'archivo' in request.FILES:
                    nfileDocumento = request.FILES['archivo']
                    extensionDocumento = nfileDocumento._name.split('.')
                    tamDocumento = len(extensionDocumento)
                    exteDocumento = extensionDocumento[tamDocumento - 1]
                    if nfileDocumento.size > 26214400:
                        raise NameError(u"Error al cargar, el archivo es mayor a 25 Mb.")
                    if not exteDocumento.lower() in ['py']:
                        raise NameError(u"Error al cargar, solo se permiten archivos .py")
                    nfileDocumento._name = generar_nombre("archivo_proceso", nfileDocumento._name)

                    PythonProcess_n.archivo = nfileDocumento
                PythonProcess_n.save(request)

                # log(u'Agregó un proceso para ejecutar %s -%s' % (PythonProcess_n.__str__(), PythonProcess_n.pk), request, 'add')
                return JsonResponse({'result': True, 'mensaje': u'Registro guardado con éxito!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse(
                    {'result': False, 'mensaje': u'Error al procesar los datos! Detalle: %s' % (ex.__str__())})
        elif action == 'editprocess':
            try:
                id = encrypt(request.POST['id'])
                data['filtro'] = filtro = PythonProcess.objects.filter(pk=int(id), status=True).first()
                if not filtro:
                    raise NameError('Porceso no encontrado')
                f = ProcesoPythonForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                if PythonProcess.objects.filter(status=True, nombre=f.cleaned_data['nombre'],
                                                descripcion=f.cleaned_data['descripcion'],
                                                tipo=f.cleaned_data['tipo']).exclude(id=id):
                    raise NameError('Y existe este proceso')
                filtro.nombre = f.cleaned_data['nombre']
                filtro.descripcion = f.cleaned_data['descripcion']
                filtro.tipo = f.cleaned_data['tipo']
                filtro.code = f.cleaned_data['code']
                if 'anexo' in request.FILES:
                    nfileDocumento = request.FILES['anexo']
                    extensionDocumento = nfileDocumento._name.split('.')
                    tamDocumento = len(extensionDocumento)
                    exteDocumento = extensionDocumento[tamDocumento - 1]
                    if nfileDocumento.size > 26214400:
                        raise NameError(u"Error al cargar, el archivo es mayor a 25 Mb.")
                    if not exteDocumento.lower() in ['xls', 'xlsx']:
                        raise NameError(u"Error al cargar, solo se permiten archivos .xls, .xlsx")
                    nfileDocumento._name = generar_nombre("anexo_proceso", nfileDocumento._name)

                    filtro.anexo = nfileDocumento
                if 'archivo' in request.FILES:
                    nfileDocumento = request.FILES['archivo']
                    extensionDocumento = nfileDocumento._name.split('.')
                    tamDocumento = len(extensionDocumento)
                    exteDocumento = extensionDocumento[tamDocumento - 1]
                    if nfileDocumento.size > 26214400:
                        raise NameError(u"Error al cargar, el archivo es mayor a 25 Mb.")
                    if not exteDocumento.lower() in ['py']:
                        raise NameError(u"Error al cargar, solo se permiten archivos .py")
                    nfileDocumento._name = generar_nombre("archivo_proceso", nfileDocumento._name)

                    filtro.archivo = nfileDocumento
                filtro.save(request)
                # log(u'Editó un proceso para ejecutar %s -%s' % (filtro.__str__(), filtro.pk), request, 'edit')
                return JsonResponse({'result': True, 'mensaje': u'Registro guardado con éxito!', 'modalsuccess': True})
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': ex})
        elif action == 'execute':
            with transaction.atomic():
                try:
                    data['id'] = id = request.POST['id'] if 'id' in request.POST else 0
                    proc = PythonProcess.objects.filter(status=True, id=id).first()
                    if not proc.usuario_creacion == request.user:
                        raise NameError('Lo sentimos, este proceso solo puede ser ejecutado por su creador')
                    noti = Notificacion(cuerpo='Se encuentra ejecutando un proceso de python {}'.format(proc.nombre if proc else ''),
                                        titulo='Ejecución de proceso de python {}'.format(proc.nombre if proc else ''), destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    ejecutar_procesos_background(request=request, data=data, notiid=noti.pk).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El proceso se está ejecutando en segundo plano. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Ocurrió un error y se canceló el proceso {}".format(ex)})
        elif action == 'deleteprocess':
            try:
                id = encrypt(request.POST['id'])
                data['filtro'] = filtro = PythonProcess.objects.filter(pk=int(id), status=True).first()
                if not filtro:
                    raise NameError('Porceso no encontrado')
                # log(u'Eliminó un proceso de python ejecutable %s -%s' % (filtro.__str__(), filtro.pk), request, 'del')
                filtro.delete()
                return JsonResponse({'error': False, 'mensaje': u'Registro eliminado con éxito!'})
            except Exception as ex:
                return JsonResponse({'error': True, 'mensaje': ex})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['titulo'] = u'Agregar proceso de Python'
                    data['action'] = action
                    data['form'] = ProcesoPythonForm()
                    template = get_template('ejecucionprocesos/form.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                    # return render(request, "ejecucionprocesos/form.html", data)
                except Exception as ex:
                    pass
            elif action == 'editprocess':
                try:
                    id = encrypt(request.GET['id'])
                    data['action'] = action
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PythonProcess.objects.filter(pk=int(id), status=True).first()
                    data['titulo'] = u'Editar porceso python'
                    form = ProcesoPythonForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    form.edit(filtro.id)
                    template = get_template('ejecucionprocesos/form.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass
        else:
            data['title'] = u'Procesos de python'
            search = None
            procesos = PythonProcess.objects.filter(status=True, usuario_creacion=request.user).distinct().order_by('-fecha_modificacion')
            data['procesos'] = procesos
            data['search'] = search if search else ""
            return render(request, "ejecucionprocesos/view.html", data)
