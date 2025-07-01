from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import SolRetMatRevisionesForm, ReporteEstudiantesRetiradosForm
from sga.funciones import MiPaginador, generar_nombre, puede_realizar_accion, log
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import SolicitudRetiroMatricula, SolicitudRetiroMatriculaRevision, Matricula, Nivel, Carrera, \
    SolicitudMateriaRetirada, MateriaAsignada
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addaprobar_o_rechazar':
                try:
                    if puede_registrar(request):
                        solicitud = SolicitudRetiroMatricula.objects.db_manager("sga_select").get(~Q(estado_solicitud=SolicitudRetiroMatricula.RECHAZADO), pk=int(encrypt(request.POST['solicitud_id'])))
                        registrar_revision = puede_registrar_revision(request, persona, solicitud)
                        if registrar_revision['puede_revisar']:
                            form = SolRetMatRevisionesForm(request.POST, request.FILES)
                            #preguntar si es obligacion subir archivo
                            if not registrar_revision['debe_subir_archivo']:
                                # si no es obligatorio subir archivo
                                form.noingresararchivo()
                            if form.is_valid():
                                srmr = SolicitudRetiroMatriculaRevision(
                                    persona_que_revisa_id = persona.id,
                                    solicitud=solicitud,
                                    observaciones=form.cleaned_data['observaciones'],
                                    estado_solicitud=form.cleaned_data['estado_solicitud'],
                                    cargo_persona=registrar_revision['cargo'],
                                )
                                srmr.save()
                                if registrar_revision['debe_subir_archivo']:
                                    newfile = request.FILES['archivo']
                                    newfile._name = generar_nombre("archivorevisionsolicitudretiromatricula_", newfile._name)
                                    srmr.archivo = newfile
                                    srmr.save()
                                query_srmr = SolicitudRetiroMatriculaRevision.objects.db_manager('sga_select').filter(solicitud=solicitud)
                                if query_srmr.filter(estado_solicitud=srmr.RECHAZADO).count() > 0 or srmr.estado_solicitud == srmr.RECHAZADO:#Comprobar si al menos una de las revisiones ha sido rechazada
                                    solicitud.estado_solicitud = solicitud.RECHAZADO#Se rechazará la solicitud automáticamente y el estudiante debe enviar otra
                                    solicitud.save()
                                elif query_srmr.count() == 3 and query_srmr.filter(estado_solicitud=srmr.APROBADO).count() == 3:#Comprobar las 3 revisiones fueron aprobadas
                                    solicitud.estado_solicitud = solicitud.APROBADO#Se aprobará la solicitud automáticamente y el estudiante quedará fuera de la matrícula
                                    solicitud.save()
                                log(u'Se revisó la solicitud de retiro de matrícula del estudiante %s - estado: %s' % (solicitud.matricula.inscripcion, srmr.ver_estado_solicitud()), request, "addaprobar_o_rechazar")
                                return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass
            elif action == 'sec_elimina_matricula':
                try:
                    if puede_registrar(request):
                        solicitud = SolicitudRetiroMatricula.objects.db_manager("sga_select").get(~Q(estado_solicitud=SolicitudRetiroMatricula.RECHAZADO), pk=int(encrypt(request.POST['solicitud_id'])))
                        registrar_revision = puede_registrar_revision(request, persona, solicitud)
                        puede_eliminar_matricula = registrar_revision['puede_eliminar_matricula']
                        if puede_eliminar_matricula:
                            materias_asignadas = solicitud.ver_materias_asignadas()
                            matricula = Matricula.objects.get(id=solicitud.matricula.id)
                            matricula.retiradomatricula = True
                            for ma in materias_asignadas:
                                materiaasignada = MateriaAsignada.objects.get(id=ma.materia_asignada.id, matricula_id=matricula.id)
                                matricula.eliminar_materia(materiaasignada, request)
                            matricula.save()
                            solicitud.fecha_retiro = datetime.now()
                            solicitud.save()
                            log(u'Retiró la matrícula del estudiante %s' % matricula.inscripcion, request, "sec_elimina_matricula")
                            return JsonResponse({"result": "ok", "mensaje": "Se retiró al estudiante de la matrícula [%s] correctamente" % (matricula)})
                except Exception as ex:
                    pass
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
    elif request.method == 'GET':
        #Consultar si es decano, secretaría general o bienestar
        solicitudes = SolicitudRetiroMatricula.objects.none()
        search = None
        ids = None
        filtro = None
        data['title'] = u'Aprobación de solicitudes de retiro de matrícula'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'verdetalle':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudRetiroMatricula.objects.db_manager("sga_select").get(pk=int(encrypt(request.GET['id'])))
                    data['solicitudes'] = SolicitudRetiroMatricula.objects.db_manager("sga_select").filter(matricula=solicitud.matricula).order_by('id')
                    template = get_template("adm_solicitudretiromatricula/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            elif action == 'aprobar_o_rechazar':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudRetiroMatricula.objects.db_manager("sga_select").get(pk=int(encrypt(request.GET['id'])))
                    data['detallesolicitud'] = detallesolicitud = SolicitudRetiroMatriculaRevision.objects.db_manager("sga_select").filter(solicitud=solicitud).order_by('id')
                    data['fecha'] = datetime.now()
                    data['aprobador'] = persona.nombre_completo()
                    registrar_revision = puede_registrar_revision(request, persona, solicitud)
                    if registrar_revision['puede_revisar']:
                        form = SolRetMatRevisionesForm()
                        if not registrar_revision['debe_subir_archivo']:
                            #si no es obligatorio subir archivo
                            form.noingresararchivo()
                        data['form'] = form
                        data['debe_subir_archivo'] = registrar_revision['debe_subir_archivo']
                    data['puede_registrar_revision'] = registrar_revision['puede_revisar'] and solicitud.estado_solicitud != solicitud.RECHAZADO
                    data['matricula_retirada'] = matricula_retirada = solicitud.matricula.retiradomatricula
                    data['puede_eliminar_matricula'] = registrar_revision['puede_eliminar_matricula'] and not matricula_retirada
                    template = get_template("adm_solicitudretiromatricula/aprobar_o_rechazar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'puede_registrar_revision': data['puede_registrar_revision']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            elif action == 'sec_elimina_matricula':
                try:
                    data['matricula'] = matricula = Matricula.objects.db_manager("sga_select").get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_solicitudretiromatricula/delmatricula.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'matricula_json':'{"action": "sec_elimina_matricula", "matricula_id": "%s", "solicitud_id": "%s"}' % (request.GET['id'], request.GET['solicitud_id'])})
                except Exception as ex:
                    pass
            elif action == 'retornarniveles':
                id = int(request.GET['id'])
                niveles = []
                for n in Matricula.objects.filter(inscripcion__carrera_id=id,status=True, nivel__status=True).distinct('nivel_id').order_by("nivel_id"):
                    niveles.append({"id": n.nivel.id, "desc": "%s | %s" % (n.nivel.periodo.nombre,  n.nivel.__str__())})
                return JsonResponse({"result": "ok", "niveles": niveles}, safe=False)
            elif action == 'reporte_est_ret':
                try:
                    data['fecha_desde'] = request.GET['fecha_desde']
                    data['fecha_hasta'] = request.GET['fecha_hasta']
                    fecha_desde = datetime.strptime(request.GET['fecha_desde'], "%d-%m-%Y").strftime("%Y-%m-%d")
                    fecha_hasta = datetime.strptime(request.GET['fecha_hasta'], "%d-%m-%Y").strftime("%Y-%m-%d")
                    data['nivel'] = nivel = Nivel.objects.db_manager("sga_select").get(id=int(request.GET['nivel']))
                    data['carrera'] = carrera = Carrera.objects.db_manager("sga_select").get(id=int(request.GET['carrera']))
                    data['retirados'] = retirados = SolicitudRetiroMatricula.objects.db_manager("sga_select").filter(matricula__retiradomatricula = True,
                                                                                                 matricula__nivel_id=nivel.id,
                                                                                                 matricula__inscripcion__carrera_id=carrera.id,
                                                                                                 fecha_retiro__range=(fecha_desde, fecha_hasta)
                                                                                                 ).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    return conviert_html_to_pdf(
                        'adm_solicitudretiromatricula/reporte_retirados_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

        if 's' in request.GET:
            search = request.GET['s'].strip()
            ss = search.split(' ')
            solicitudes = SolicitudRetiroMatricula.objects.filter(Q(matricula__inscripcion__persona__cedula__icontains=search)|
                                                                  Q(matricula__inscripcion__persona__apellido1__icontains=search)|
                                                                  Q(matricula__inscripcion__persona__apellido2__icontains=search)|
                                                                  Q(matricula__inscripcion__persona__nombres__icontains=search)).order_by('-id')
        else:
            solicitudes = SolicitudRetiroMatricula.objects.all().order_by('-id')
        if 'g' in request.GET:
            filtro = request.GET['g']
            if filtro == 'POR_APROBAR':
                solicitudes = solicitudes.filter(~Q(estado_solicitud__in=(SolicitudRetiroMatricula.APROBADO, SolicitudRetiroMatricula.RECHAZADO)))
            elif filtro== 'APROBADOS':
                solicitudes = solicitudes.filter(estado_solicitud=SolicitudRetiroMatricula.APROBADO)
            elif filtro== 'RECHAZADOS':
                solicitudes = solicitudes.filter(estado_solicitud=SolicitudRetiroMatricula.RECHAZADO)
            else:
                filtro = None

        data['solicitudes'] = solicitudes
        paging = MiPaginador(solicitudes, 20)
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
        data['g'] = filtro if filtro else ""
        data['reporte_form'] = ReporteEstudiantesRetiradosForm()
        return render(request,'adm_solicitudretiromatricula/view.html', data)

def puede_registrar_revision(request, persona, solicitud):
    #preguntar permisos
    salida = {'puede_revisar':False,'debe_subir_archivo':False,'cargo': 0, 'puede_eliminar_matricula':False}
    query_srmr = SolicitudRetiroMatriculaRevision.objects.db_manager("sga_select").filter(solicitud=solicitud)
    es = SolicitudRetiroMatriculaRevision
    if request.user.has_perm('sga.puede_gestionar_retiro_matricula_secretaria'):#Es de Seretaría General
        #retorna si no hay registros de secretaría general
        salida['puede_eliminar_matricula'] = query_srmr.filter(estado_solicitud=es.APROBADO).count()==3
        salida['puede_revisar'] = not query_srmr.filter(persona_que_revisa=persona, cargo_persona=es.SECRETARIA_GENERAL).exists()
        salida['cargo'] = es.SECRETARIA_GENERAL
        if salida['puede_revisar']:
            if solicitud.estado_solicitud == solicitud.ENVIADO:
                solicitud.estado_solicitud = solicitud.SOLICITADO
                solicitud.save()
    elif request.user.has_perm('sga.puede_gestionar_retiro_matricula_decano'):#Es Decano
        # retorna si no hay registros del decano y que secretaría general ya haya revisado primero la solicitud para poder revisarlo
        salida['puede_revisar'] = not query_srmr.filter(persona_que_revisa=persona, cargo_persona=es.DECANO).exists() and query_srmr.filter(cargo_persona=es.SECRETARIA_GENERAL).exists()
        salida['cargo'] = es.DECANO
        salida['debe_subir_archivo'] = True
        if salida['puede_revisar']:
            if solicitud.estado_solicitud == solicitud.SOLICITADO:
                solicitud.estado_solicitud = solicitud.REVISION_FACULTAD
                solicitud.save()
    elif request.user.has_perm('sga.puede_gestionar_retiro_matricula_bienestar'):#Es de Bienestar
        # retorna si no hay registros de BIENESTAR y que SECRETARÍA GENERAL junto al DECANO ya hayan revisado primero la solicitud para poder revisarlo
        salida['puede_revisar'] = not query_srmr.filter(persona_que_revisa=persona, cargo_persona=es.BIENESTAR).exists() and query_srmr.filter(cargo_persona=es.SECRETARIA_GENERAL).exists() and query_srmr.filter(cargo_persona=es.DECANO).exists()
        salida['cargo'] = es.BIENESTAR
        salida['debe_subir_archivo'] = True
        if salida['puede_revisar']:
            if solicitud.estado_solicitud == solicitud.REVISION_FACULTAD:
                solicitud.estado_solicitud = solicitud.REVISION_BIENESTAR
                solicitud.save()
    return salida

def puede_registrar(request):
    if request.user.has_perm('sga.puede_gestionar_retiro_matricula_secretaria') or request.user.has_perm('sga.puede_gestionar_retiro_matricula_decano') or request.user.has_perm('sga.puede_gestionar_retiro_matricula_bienestar'):
        return True
    else:
        puede_realizar_accion(request, 'sga.puede_gestionar_retiro_matricula_secretaria')
        puede_realizar_accion(request, 'sga.puede_gestionar_retiro_matricula_decano')
        puede_realizar_accion(request, 'sga.puede_gestionar_retiro_matricula_bienestar')