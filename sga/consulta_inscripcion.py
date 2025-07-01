# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import USA_TIPOS_INSCRIPCIONES, CONTROL_UNICO_CREDENCIALES, \
    MATRICULACION_LIBRE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador
from sga.models import Inscripcion, Grupo, Carrera, Coordinacion, MateriaAsignada

unicode =str

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    personasesion = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de inscripciones'
        persona = request.session['persona']
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'ver_notas':
                try:
                    data['inscripcion'] = Inscripcion.objects.filter(id=request.GET['idinscripcion'])[0]
                    data['materiasasignadas'] = maateriaasignada = MateriaAsignada.objects.filter(id=request.GET['idcurso'])
                    data['matricula'] = maateriaasignada[0].matricula
                    return render(request, "consulta_inscripcion/ver_notas.html", data)
                except Exception as ex:
                    pass
            elif action == 'seguimiento_asignaturas_alumno':
                try:
                    data['title'] = u'Asignaturas'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['materiaasignadas'] = inscripcion.materias(periodo)
                    return render(request, "consulta_inscripcion/asignaturas_alumno.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                facultad_admision = 9
                data['title'] = u'Listado de inscripciones'
                persona = request.session['persona']
                carreras_admision = Coordinacion.objects.get(pk=facultad_admision).carreras()
                carreras = Carrera.objects.filter(status=True).exclude(pk__in=carreras_admision)
                search = None
                carreraselect = 0
                listacarreras = []
                estado_todos = False
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    if carreraselect > 0:
                        listacarreras.append(carreraselect)
                    else:
                        estado_todos = True
                else:
                    estado_todos = True
                if estado_todos:
                    for carrera in carreras:
                        listacarreras.append(carrera)
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        inscripciones = Inscripcion.objects.filter(Q(persona__nombres__icontains=search) |
                                                                   Q(persona__apellido1__icontains=search) |
                                                                   Q(persona__apellido2__icontains=search) |
                                                                   Q(persona__cedula__icontains=search) |
                                                                   Q(persona__pasaporte__icontains=search) |
                                                                   Q(identificador__icontains=search) |
                                                                   Q(inscripciongrupo__grupo__nombre__icontains=search) |
                                                                   Q(persona__usuario__username__icontains=search), carrera__in=listacarreras).distinct().exclude(carrera__coordinacion__id=9)
                    else:
                        inscripciones = Inscripcion.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                   Q(persona__apellido2__icontains=ss[1]), carrera__in=listacarreras).distinct().exclude(carrera__coordinacion__id=9)
                elif 'n' in request.GET:
                    search = request.GET['n']
                    ss = search.split(' ')
                    if len(ss) == 2:
                        inscripciones = Inscripcion.objects.filter(persona__nombres=search, carrera__in=listacarreras).distinct().exclude(carrera__coordinacion__id=9)
                    else:
                        inscripciones = Inscripcion.objects.all(carrera__in=listacarreras)
                elif 'g' in request.GET:
                    data['grupo'] = Grupo.objects.get(pk=request.GET['g'])
                    inscripciones = Inscripcion.objects.filter(inscripciongrupo__grupo=data['grupo'], carrera__in=listacarreras).exclude(carrera__coordinacion__id=9)
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    inscripciones = Inscripcion.objects.filter(id=ids, carrera__in=listacarreras).exclude(carrera__coordinacion__id=9)
                else:
                    inscripciones = Inscripcion.objects.filter(carrera__in=listacarreras).exclude(carrera__coordinacion__id=9)
                paging = MiPaginador(inscripciones, 15)
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
                data['inscripciones'] = page.object_list
                data['control_unico_credenciales'] = CONTROL_UNICO_CREDENCIALES
                data['usa_tipos_inscripciones'] = USA_TIPOS_INSCRIPCIONES
                data['matriculacion_libre'] = MATRICULACION_LIBRE
                data['periodo'] = request.session['periodo']
                data['carreraselect'] = carreraselect
                data['carreras'] = carreras
                return render(request, "consulta_inscripcion/view.html", data)
            except Exception as ex:
                pass