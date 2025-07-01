# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_SYLLABUS
from sga.commonviews import adduserdata
from sga.forms import ArchivoSyllabusForm
from sga.funciones import MiPaginador, generar_nombre, log, puede_realizar_accion
from sga.models import Archivo, ProfesorMateria

unicode = str
@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    # miscarreras = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
    miscarreras = persona.mis_carreras()
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addsyllabus':
                try:
                    form = ArchivoSyllabusForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("silabo_", newfile._name)
                        profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                        archivo = Archivo(nombre=form.cleaned_data['nombre'],
                                          materia=profesormateria.materia,
                                          fecha=datetime.now().date(),
                                          archivo=newfile,
                                          tipo_id=ARCHIVO_TIPO_SYLLABUS,
                                          profesor=profesormateria.profesor)
                        archivo.save(request)
                        log(u'Adiciono silabo: %s' % archivo, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsyllabus':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_silabos')
                    data['title'] = u'Adicionar sílabo'
                    profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
                    data['profesormateria'] = profesormateria
                    data['form'] = ArchivoSyllabusForm(initial={'nombre': unicode(profesormateria.materia)})
                    return render(request, "cons_documentos/addsyllabus.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Sílabos de materias'
            search = None
            if 's' in request.GET:
                search = request.GET['s']
                profesormaterias = ProfesorMateria.objects.filter(Q(materia__nivel__carrera__in=miscarreras) | Q(materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).filter(Q(profesor__persona__nombres__icontains=search) |
                                                                                                                                                                                                        Q(profesor__persona__apellido1__icontains=search) |
                                                                                                                                                                                                        Q(materia__asignatura__nombre__icontains=search) |
                                                                                                                                                                                                        Q(profesor__persona__apellido2__icontains=search), activo=True, principal=True, materia__nivel__periodo=periodo).distinct().order_by('profesor')
            else:
                profesormaterias = ProfesorMateria.objects.filter(Q(materia__nivel__carrera__in=miscarreras) | Q(materia__nivel__nivellibrecoordinacion__coordinacion__carrera__in=miscarreras)).filter(materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
            paging = MiPaginador(profesormaterias, 25)
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
            data['profesormaterias'] = page.object_list
            data['search'] = search if search else ""
            return render(request, "cons_documentos/view.html", data)