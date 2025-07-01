# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import json
from django.template import Context
from django.template.loader import get_template
from datetime import datetime
from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from sga.commonviews import adduserdata
from sga.forms import SolicitudForm
from django.db.models.aggregates import Avg
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import RecordAcademico, SolicitudMatricula, SolicitudDetalle, Matricula, MateriaAsignada, TipoSolicitud, \
    ConfiguracionTerceraMatricula
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    valid, msg_error = valid_intro_module_estudiante(request, 'pregrado')
    if not valid:
        return HttpResponseRedirect(f"/?info={msg_error}")
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                if 'adjunto' in request.FILES:
                    newfile = request.FILES['adjunto']
                    extencion = newfile._name.split('.')
                    exte = extencion[1]
                    if newfile.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error archivo mayor a 2Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                f = SolicitudForm(request.POST)
                if f.is_valid():
                    tipo = f.cleaned_data['tiposolicitud']
                    if tipo.para_pdf:
                        if 'adjunto' not in request.FILES:
                            return JsonResponse({"result": "bad", "mensaje": u"Por favor subir archivos"})
                    configuracionterceramatricula = ConfiguracionTerceraMatricula.objects.get(pk=int(encrypt(request.POST['idc'])))
                    if not configuracionterceramatricula.activa:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya no se encuentra activo las 3ra matriculas."})
                    solicitudmatricula = SolicitudMatricula(descripcion=f.cleaned_data['descripcion'],
                                                            tiposolicitud=f.cleaned_data['tiposolicitud'],
                                                            inscripcion=inscripcion,
                                                            configuracionterceramatricula=configuracionterceramatricula,
                                                            estadosolicitud=1)
                    solicitudmatricula.save(request)
                    if 'adjunto' in request.FILES:
                        newfile = request.FILES['adjunto']
                        newfile._name = generar_nombre("adjunto_", newfile._name)
                        solicitudmatricula.adjunto = newfile
                        solicitudmatricula.save(request)
                    asignaturas = RecordAcademico.objects.filter(inscripcion=inscripcion, matriculas=2, aprobada=False, asignaturamalla_id__isnull=False).order_by('asignatura__nombre')
                    if asignaturas:
                        for asignatura in asignaturas:
                            solicituddetalle = SolicitudDetalle(solicitudmatricula=solicitudmatricula,
                                                                asignatura=asignatura.asignatura)
                            solicituddetalle.save(request)
                    log(u'Alumno adiciono solicitud en solicitud matricula: %s [%s]' % (solicitudmatricula, solicitudmatricula.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'delsolicitud':
            try:
                solicitud = SolicitudMatricula.objects.get(pk=int(encrypt(request.POST['id'])))
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'validaliterales':
            try:
                idinscripcion = request.POST['idinscripcion']
                tiposol = TipoSolicitud.objects.get(pk=request.POST['tiposolicitudid'])
                if Matricula.objects.filter(inscripcion_id=idinscripcion,status=True).exists():
                    matricula = Matricula.objects.filter(inscripcion_id=idinscripcion,status=True).order_by('-id')[0]
                    if tiposol.validar:
                        numrecord = RecordAcademico.objects.filter(asignaturamalla__isnull=False, inscripcion=idinscripcion, matriculas=2, aprobada=False)[0]
                        numeroreprobadasterceras = RecordAcademico.objects.filter(asignaturamalla__isnull=False,inscripcion=idinscripcion, matriculas=2, aprobada=False).count()
                        listaasinaturas = RecordAcademico.objects.values_list('modulomalla__asignatura__id', flat=True).filter(modulomalla__isnull=False, inscripcion=idinscripcion, aprobada=False)
                        # if listaasinaturas:
                        #     asignada = MateriaAsignada.objects.filter(matricula=matricula, status=True, materiaasignadaretiro__isnull=True).exclude(materia__asignatura__id__in=listaasinaturas)
                        # else:
                        #     asignada = MateriaAsignada.objects.filter(matricula=matricula, status=True, materiaasignadaretiro__isnull=True)
                        numeroreprobadasnormales = RecordAcademico.objects.filter(asignaturamalla__isnull=False,aprobada=False, inscripcion=idinscripcion,asignaturamalla__nivelmalla=numrecord.asignaturamalla.nivelmalla).exclude( materiaregular=numrecord.materiaregular).exclude(asignatura_id__in=listaasinaturas).count()
                        # numeroreprobadasterceras = asignada.filter(matriculas=2, estado_id__in=[2, 3, 4]).count()
                        if tiposol.id == 1:
                            if numeroreprobadasnormales == 0:
                                if numeroreprobadasterceras == 1:
                                    # totalpromedio = round(asignada.filter(matriculas=1).aggregate(promedio=Avg('notafinal'))['promedio'], 0)
                                    totalpromedio = round(RecordAcademico.objects.filter(asignaturamalla__isnull=False, inscripcion=idinscripcion,asignaturamalla__nivelmalla=numrecord.asignaturamalla.nivelmalla).exclude( materiaregular=numrecord.materiaregular).aggregate(promedio=Avg('nota'))['promedio'], 0)
                                    if totalpromedio >= 75:
                                        result = {'result': 'ok'}
                                    else:
                                        result = {'result': 'bad','mensaje': tiposol.descripcion + '<br><br>' + 'Su promedio de calificacion es menor a 75'}
                                else:
                                    numrecord = RecordAcademico.objects.filter(asignaturamalla__isnull=False,inscripcion=idinscripcion,matriculas=2, aprobada=False)[0]
                                    totalrep = RecordAcademico.objects.filter(asignaturamalla__isnull=False,inscripcion=idinscripcion,matriculas=2, aprobada=False).count()
                                    totalpromedio = round(RecordAcademico.objects.filter(asignaturamalla__isnull=False,inscripcion=idinscripcion,asignaturamalla__nivelmalla=numrecord.asignaturamalla.nivelmalla).exclude(materiaregular=numrecord.materiaregular).aggregate(promedio=Avg('nota'))['promedio'],0)
                                    if totalrep == 1:
                                        if totalpromedio >= 75:
                                            result = {'result': 'ok'}
                                        else:
                                            result = {'result': 'bad','mensaje': tiposol.descripcion + '<br><br>' + 'Su promedio de calificacion es menor a 75'}
                                    else:
                                        result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada mas de una materia'}
                            else:
                                result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada una materia o mas'}
                        else:
                            if tiposol.id == 2:
                                if numeroreprobadasnormales == 0:
                                    if numeroreprobadasterceras == 1:
                                        # totalasistencia = round(asignada.filter(matriculas=2).aggregate(promedio=Avg('asistenciafinal'))['promedio'])
                                        totalasistencia = round(RecordAcademico.objects.filter(asignaturamalla__isnull=False,inscripcion=idinscripcion, matriculas=2, aprobada=False).aggregate(promedio=Avg('asistencia'))['promedio'])
                                        if totalasistencia >= 90:
                                            result = {'result': 'ok'}
                                        else:
                                            result = {'result': 'bad','mensaje': tiposol.descripcion + '<br><br>' + 'Su promedio de asistencia es menor a 90'}
                                    else:
                                        numrecord = RecordAcademico.objects.filter(asignaturamalla__isnull=False,inscripcion=idinscripcion, matriculas=2, aprobada=False)[0]
                                        totalrep = RecordAcademico.objects.filter(asignaturamalla__isnull=False,inscripcion=idinscripcion, matriculas=2, aprobada=False).count()
                                        totalasistencia = round(RecordAcademico.objects.filter(asignaturamalla__isnull=False,inscripcion=idinscripcion, asignaturamalla__nivelmalla=numrecord.asignaturamalla.nivelmalla).exclude(materiaregular=numrecord.materiaregular).aggregate(promedio=Avg('asistencia'))['promedio'], 0)
                                        if totalrep == 1:
                                            if totalasistencia >= 90:
                                                result = {'result': 'ok'}
                                            else:
                                                result = {'result': 'bad',  'mensaje': tiposol.descripcion + '<br><br>' + 'Su promedio de asistencia es menor a 90'}
                                        else:
                                            result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada mas de una materia'}
                                else:
                                    result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada una materia o mas'}
                    else:
                        result = {'result': 'ok'}
                else:
                    if RecordAcademico.objects.filter(inscripcion_id=idinscripcion, status=True).exists():
                        record = RecordAcademico.objects.filter(inscripcion_id=idinscripcion, status=True)
                        numeroreprobadasnormales = record.filter(matriculas=1, aprobada=False).count()
                        numeroreprobadasterceras = record.filter(matriculas=2, aprobada=False).count()
                        if tiposol.validar:
                            if tiposol.id == 1:
                                if numeroreprobadasnormales == 0:
                                    if numeroreprobadasterceras == 1:
                                        totalpromedio = round(record.filter(matriculas=1).aggregate(promedio=Avg('nota'))['promedio'], 0)
                                        if totalpromedio >= 75:
                                            result = {'result': 'ok'}
                                        else:
                                            result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Su promedio de calificacion es menor a 75'}
                                    else:
                                        result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada mas de una materia'}
                                else:
                                    result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada una materia o mas'}
                            if tiposol.id == 2:
                                result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Su promedio de asistencia es menor a 90'}
                        else:
                            result = {'result': 'ok'}
                    else:
                        result = {'result': 'bad', 'mensaje': 'No tiene matricula'}
                # return HttpResponse(json.dumps(result), mimetype="application/json")
                return JsonResponse(result)
            except Exception as ex:
                pass
                return JsonResponse({"result": "bad"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Solicitud de Matrícula por 3ra vez'
                    data['subtitle'] = u'Art.- 112.- De conformidad con lo establecido en el Art. 84 de la Ley Orgánica de Educación Superior, se concederá matrículas por tercera ocasión en una misma asignatura o en el mismo ciclo, curso o nivel académico, solo por excepción en los siguientes casos:'
                    form = SolicitudForm()
                    data['inscripcion'] = inscripcion
                    data['asignaturas'] = RecordAcademico.objects.filter(inscripcion=inscripcion, matriculas=2, aprobada=False, asignaturamalla_id__isnull=False).order_by('asignatura__nombre')
                    data['fechaapertura'] = ConfiguracionTerceraMatricula.objects.get(pk=int(encrypt(request.GET['idc'])), status=True, activa=True)
                    data['form'] = form
                    return render(request, "alu_solicitudmatricula/ultima/addsolicitud.html", data)
                except:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitudmatricula'] = SolicitudMatricula.objects.get(pk=int(encrypt(request.GET['idsolicitud'])))
                    return render(request, "alu_solicitudmatricula/ultima/delsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'verdetalle':
                try:
                    data = {}
                    solicitud = SolicitudMatricula.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = solicitud
                    data['materiassolicitud'] = SolicitudDetalle.objects.filter(solicitudmatricula=solicitud, status=True)
                    template = get_template("alu_solicitudmatricula/ultima/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de solicitudes de última matrícula'
                search = None
                ids = None
                inscripcionid = None
                # cursor = connection.cursor()
                data['asignaturas'] = RecordAcademico.objects.filter(inscripcion=inscripcion, matriculas=2, aprobada=False, asignaturamalla_id__isnull=False).order_by('asignatura__nombre')
                data['estadoaprobacion'] = SolicitudMatricula.objects.filter(inscripcion=inscripcion, estadosolicitud=1, status=True)
                if 'id' in request.GET:
                    ids = request.GET['id']
                    solicitudmatricula = SolicitudMatricula.objects.filter(inscripcion__carrera__in=miscarreras).filter(pk=ids).order_by('nombre')
                elif 'inscripcionid' in request.GET:
                    inscripcionid = request.GET['inscripcionid']
                    solicitudmatricula = SolicitudMatricula.objects.filter(inscripcion__carrera__in=miscarreras).filter(inscripcion__id=inscripcionid)
                elif 's' in request.GET:
                    search = request.GET['s']
                    if search.isdigit():
                        solicitudmatricula = SolicitudMatricula.objects.select_related().filter(pk=search, status=True)
                    else:
                        solicitudmatricula = SolicitudMatricula.objects.select_related().filter(nombre__icontains=search, status=True)
                else:
                    solicitudmatricula = SolicitudMatricula.objects.select_related().filter(inscripcion=inscripcion,status=True).order_by('id')
                paging = MiPaginador(solicitudmatricula, 25)
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
                hoy = datetime.now().date()
                data['fechapermiso'] = ''
                if ConfiguracionTerceraMatricula.objects.values('id').filter(fechaainicio__lte=hoy, fechafin__gte=hoy, status=True, activa=True).exists():
                    apertura = True
                    mensajefecha = u'solicitud de matrícula por 3ra vez habilitada hasta:'
                    fechapermiso = ConfiguracionTerceraMatricula.objects.filter(fechaainicio__lte=hoy, fechafin__gte=hoy, status=True, activa=True)[0]
                    data['fechapermiso'] = fechapermiso
                else:
                    apertura = False
                    mensajefecha = u'Solicitud de matrícula por última vez bloqueada. Toda acción se realiza en el módulo de matriculación.'
                data['mensajefecha'] = mensajefecha
                data['apertura'] = apertura
                data['rangospaging'] = paging.rangos_paginado(p)
                data['solicitudes'] = page.object_list
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['hojavidallena'] = False if persona.hojavida_llenapracticas() else True
                data['inscripcionid'] = inscripcionid if inscripcionid else ""
                return render(request, "alu_solicitudmatricula/ultima/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "alu_solicitudmatricula/error.html", data)
