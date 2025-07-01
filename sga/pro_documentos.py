# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_DEBERES, NOTIFICACION_DEBERES, ARCHIVO_TIPO_SYLLABUS, \
    SUBIR_SILABO_DOCENTE, USA_PLANIFICACION
from sga.commonviews import adduserdata
from sga.forms import ArchivoSyllabusForm, ArchivoDeberForm, DocumentoMateriaForm
from sga.funciones import generar_nombre, log
from sga.models import LeccionGrupo, Materia, Archivo, Leccion, DocumentosMateria, miinstitucion
from sga.tasks import send_html_mail
unicode =str

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsyllabus':
            try:
                form = ArchivoSyllabusForm(request.POST, request.FILES)
                if form.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("silabo_", newfile._name)
                    materia = Materia.objects.get(pk=request.POST['materia'])
                    archivo = Archivo(nombre=form.cleaned_data['nombre'],
                                      materia=materia,
                                      fecha=datetime.now().date(),
                                      archivo=newfile,
                                      tipo_id=ARCHIVO_TIPO_SYLLABUS,
                                      profesor=profesor)
                    archivo.save(request)
                    log(u'Adiciono silabo: %s' % archivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddeberes':
            try:
                form = ArchivoDeberForm(request.POST, request.FILES)
                if form.is_valid():
                    leccion = Leccion.objects.get(pk=request.POST['leccion'])
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("deber_", newfile._name)
                    archivo = Archivo(nombre=form.cleaned_data['nombre'],
                                      materia=leccion.clase.materia,
                                      lecciongrupo=leccion.leccion_grupo(),
                                      fecha=datetime.now().date(),
                                      archivo=newfile,
                                      tipo_id=ARCHIVO_TIPO_DEBERES)
                    archivo.save()
                    if NOTIFICACION_DEBERES:
                        en_materia = []
                        for asignadomateria in leccion.clase.materia.materiaasignada_set.all():
                            en_materia.extend(asignadomateria.matricula.inscripcion.persona.lista_emails_envio())
                        send_html_mail("Nuevo deber en Clase", "emails/deber.html", {'sistema': request.session['nombresistema'], 'nombrearchivo': archivo.nombre, 't': miinstitucion(), 'f': leccion.fecha, 'd': leccion.clase.materia.profesor_actual(), 'contenido': 'Su profesor le ha asignado un deber el cual debe descargar desde el sistema de gestion academica'}, en_materia, [])
                    log(u'Adiciono deber: %s' % archivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddocumento':
            try:
                form = DocumentoMateriaForm(request.POST, request.FILES)
                if form.is_valid():
                    materia = Materia.objects.get(pk=request.POST['id'])
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("documentosmateria_", newfile._name)
                    archivo = DocumentosMateria(materia=materia,
                                                nombre=form.cleaned_data['nombre'],
                                                descripcion=form.cleaned_data['observaciones'],
                                                archivo=newfile)
                    archivo.save()
                    log(u'Adiciono documento de materia: %s' % archivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deldocumento':
            try:
                documento = DocumentosMateria.objects.get(pk=request.POST['id'])
                log(u'Elimino documento de materia: %s' % documento, request, "del")
                documento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Archivos del profesor'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsyllabus':
                try:
                    data['title'] = u'Adicionar silabo'
                    materia = Materia.objects.get(pk=request.GET['id'])
                    data['materia'] = materia
                    data['form'] = ArchivoSyllabusForm(initial={'nombre': unicode(materia.asignatura)})

                    return render(request, "pro_documentos/addsyllabus.html", data)
                except Exception as ex:
                    pass

            if action == 'syllabusmalla':
                try:
                    materia = Materia.objects.get(pk=request.GET['id'])
                    asignaturamallas = materia.syllabus_malla()
                    listado = []
                    for asignaturamalla in asignaturamallas:
                        if asignaturamalla.syllabus_actual():
                            listado.append([unicode(asignaturamalla.malla), unicode(asignaturamalla.syllabus_actual().download_link())])
                    return JsonResponse({"result": "ok", "materias": listado})
                except Exception as ex:
                    pass
                    return JsonResponse({"result": "bad"})

            elif action == 'del':
                try:
                    archivo = Archivo.objects.get(pk=request.GET['id'])
                    log(u'Elimino archivo: %s' % archivo, request, "del")
                    archivo.delete()
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    pass

            elif action == 'adddeberes':
                try:
                    data['title'] = u'Adicionar deber'
                    materia = Materia.objects.get(pk=request.GET['id'])
                    leccion = Leccion.objects.get(pk=request.GET['leccion'])
                    data['materia'] = materia
                    data['leccion'] = leccion
                    data['form'] = ArchivoDeberForm(initial={'nombre': materia.asignatura.nombre})
                    return render(request, "pro_documentos/adddeberes.html", data)
                except Exception as ex:
                    pass

            if action == 'adddocumento':
                try:
                    data['title'] = u'Adicionar documento'
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    data['form'] = DocumentoMateriaForm()
                    return render(request, "pro_documentos/adddocumento.html", data)
                except Exception as ex:
                    pass

            elif action == 'deldeber':
                try:
                    archivo = Archivo.objects.get(pk=request.GET['id'])
                    materia = archivo.materia_id
                    log(u'Elimino deber: %s' % materia, request, "del")
                    archivo.delete()
                    return HttpResponseRedirect("/pro_documentos?action=deberes&id=" + str(materia))
                except Exception as ex:
                    pass

            if action == 'deldocumento':
                try:
                    data['title'] = u'Eliminar documento'
                    data['documento'] = DocumentosMateria.objects.get(pk=request.GET['id'])
                    return render(request, "pro_documentos/deldocumento.html", data)
                except Exception as ex:
                    pass

            elif action == 'deberes':
                try:
                    data['title'] = u'Deberes por clases'
                    materia = Materia.objects.get(pk=request.GET['id'])
                    leccionesgrupo = LeccionGrupo.objects.filter(lecciones__clase__materia=materia).order_by('-fecha', '-horaentrada')
                    lecciones = Leccion.objects.filter(clase__materia=materia).order_by('-fecha', '-horaentrada')
                    paging = Paginator(lecciones, 30)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['page'] = page
                    data['leccionesgrupo'] = leccionesgrupo
                    data['lecciones'] = page.object_list
                    data['materia'] = materia
                    data['profesor'] = profesor
                    return render(request, "pro_documentos/deberes.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Documentos por materias del profesor'
            periodo = request.session['periodo']
            data['silabo_docente'] = SUBIR_SILABO_DOCENTE
            data['profesor'] = profesor
            if Materia.objects.filter(nivel__periodo=periodo, profesormateria__profesor=profesor, profesormateria__principal=True).exists():
                materias = Materia.objects.filter(nivel__periodo=periodo, profesormateria__profesor=profesor, profesormateria__principal=True).order_by('asignatura', 'nivel__sede', 'nivel__nivelmalla')
                data['materias'] = materias
                data['nivel'] = materias[0].nivel
            data['usa_planificacion'] = USA_PLANIFICACION
            return render(request, "pro_documentos/view.html", data)
