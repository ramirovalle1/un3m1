import random
from datetime import datetime, date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models.query_utils import Q
from django.db import transaction
from decorators import secure_module, last_access
from sga.forms import SacionEstudianteForm
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sagest.models import DistributivoPersona
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, generar_nombre
from sga.models import Inscripcion, Matricula, Periodo, Carrera, RegistrarVisitaGymUmeni, SacionEstudiante
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                newfile = None
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    if not exte.upper() == 'PDF':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                    if not int(request.POST['inscripcion']) > 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese el alumno"})
                    form = SacionEstudianteForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivoadjunto", newfile._name)
                        sancion = SacionEstudiante(inscripcion_id=int(request.POST['inscripcion']),
                                                   periodo=form.cleaned_data['periodo'],
                                                   fechadesde=form.cleaned_data['fechadesde'] if 'fechadesde' in request.POST else None,
                                                   fechahasta=form.cleaned_data['fechahasta'] if 'fechahasta' in request.POST else None,
                                                   observacion=form.cleaned_data['observacion'],
                                                   indifinido=form.cleaned_data['indifinido'] if 'indifinido' in request.POST else False,
                                                   archivo=newfile)
                        sancion.save(request)
                        log(u'Adicionó una nueva sancion: %s' % sancion, request,"add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                newfile = None
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    if not exte == 'pdf' or not exte == 'PDF':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                    else:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivoadjunto", newfile._name)
                form = SacionEstudianteForm(request.POST)
                if form.is_valid():
                    sancion = SacionEstudiante.objects.get(status=True, pk=int(request.POST['id']))
                    sancion.periodo_id = form.cleaned_data['periodo']
                    sancion.fechadesde = form.cleaned_data['fechadesde'] if not form.cleaned_data['periodo'] else None
                    sancion.fechahasta = form.cleaned_data['fechahasta'] if not form.cleaned_data['periodo'] else None
                    sancion.observacion = form.cleaned_data['observacion']
                    sancion.indifinido = form.cleaned_data['indifinido'] if 'indifinido' in request.POST else False
                    if newfile:
                        sancion.archivo = newfile
                    sancion.save(request)
                    log(u'Editó la sancion: %s' % sancion, request,"edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'del':
            try:
                if 'id' in request.POST:
                    sancion = SacionEstudiante.objects.get(pk=int(request.POST['id']))
                    sancion.delete()
                    log(u'Elimino la sancion: %s' % sancion, request,"del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['title'] = u'Adicionar sanción'
                    data['form'] =  SacionEstudianteForm()
                    return render(request, "adm_sancionestudiante/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar sanción'
                    data['sancion'] = sancion = SacionEstudiante.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = SacionEstudianteForm(initial={'inscripcion':sancion.inscripcion.id,
                                                                  'periodo':sancion.periodo,
                                                                  'fechadesde':sancion.fechadesde,
                                                                  'fechahasta':sancion.fechahasta,
                                                                  'observacion':sancion.observacion,
                                                                  'indifinido':sancion.indifinido,
                                                                  'archivo':sancion.archivo})
                    form.editar(sancion)
                    data['form'] = form
                    return render(request, "adm_sancionestudiante/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'del':
                try:
                    data['title'] = u'Eliminar la sanción'
                    data['sancion'] = SacionEstudiante.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_sancionestudiante/del.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Sanciones de estudiantes'
            try:
                search=None
                ids =None
                fecha = None
                sanciones = SacionEstudiante.objects.filter(status=True)
                if 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    sanciones = sanciones.filter(pk=ids)
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        sanciones = sanciones.filter(Q(inscripcion__persona__nombres__icontains=search)| Q(inscripcion__persona__apellido1__icontains=search)|Q(inscripcion__persona__apellido2__icontains=search)| Q(inscripcion__persona__cedula__icontains=search))
                    else:
                        sanciones = sanciones.filter((Q(inscripcion__persona__nombres__icontains=ss[0])& Q(inscripcion__persona__nombres__icontains=ss[1]))|(Q(inscripcion__persona__apellido1__icontains=ss[0])& Q(inscripcion__persona__apellido1__icontains=ss[1])))
                paging = MiPaginador(sanciones, 20)
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
                data['sanciones'] = page.object_list
                data['fechaselect'] = fecha
                return render(request, "adm_sancionestudiante/view.html", data)
            except Exception as ex:
                pass


