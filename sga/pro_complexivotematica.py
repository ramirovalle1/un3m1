# -*- coding: UTF-8 -*-
from datetime import timedelta, datetime
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Sum
from django.template import Context
from django.template.loader import get_template

from sagest.models import DistributivoPersona
from sga.commonviews import adduserdata
from sga.forms import ComplexivoAcompanamientoForm, ComplexivoCalificarPropuestaForm, \
    ComplexivoCalificacionSustentacionForm
from sga.funciones import log, generar_nombre, null_to_numeric, null_to_decimal
from sga.funciones_templatepdf import actatribunalcalificacion, rubricatribunalcalificacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import ComplexivoGrupoTematica, ComplexivoAcompanamiento, PeriodoGrupoTitulacion, ArchivoTitulacion, \
    ComplexivoExamen, AlternativaTitulacion, ComplexivoExamenDetalle, ComplexivoPropuestaPractica, \
    ComplexivoPropuestaPracticaArchivo, ComplexivoDetalleGrupo, MESES_CHOICES, CargoInstitucion, Graduado, \
    ExamenComlexivoGraduados, RubricaTitulacion, CalificacionRubricaTitulacion, CalificacionDetalleRubricaTitulacion, \
    ModeloRubricaTitulacion, CalificacionDetalleModeloRubricaTitulacion
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db import transaction
from xlwt import *
from sga.templatetags.sga_extras import encrypt

from decorators import secure_module
import json

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    profesor = perfilprincipal.profesor

    # bordes
    borders = Borders()
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1
    # estilos para los reportes
    title = easyxf('font: name Arial, bold on , height 200; alignment: horiz centre')
    subtitle = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    normaliz = easyxf('font: name Arial , height 150; align: wrap on,horiz left ')
    nnormal = easyxf('font: name Arial, bold on , height 150; align: wrap on,horiz right')
    normal = easyxf('font: name Arial , height 150; align: wrap on,horiz center ')
    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    stylebnombre = easyxf('font: name Arial, bold on , height 150; align: wrap on, horiz left')
    stylebnotas.borders = borders
    normaliz.borders = borders

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'add' or action == 'edit':
                try:
                    f = ComplexivoAcompanamientoForm(request.POST)
                    if f.is_valid():
                        if action == 'add':
                            acompanamiento = ComplexivoAcompanamiento()
                            grupo = ComplexivoGrupoTematica.objects.get(pk=request.POST['id'])
                            acompanamiento.grupo = grupo
                            if grupo.hora_registrada(f.cleaned_data['horainicio'],f.cleaned_data['fecha'] ):
                                return JsonResponse({'result': 'bad','mensaje': u'Ya se ha registrado un acompañamiento en estas horas.'})
                            if f.cleaned_data['horas'] > grupo.horas_restantes_fecha(f.cleaned_data['fecha'], None):
                                return JsonResponse({'result': 'bad','mensaje': u'La cantidad de horas supera el maximo pèrmitido por día.'})
                        else:
                            acompanamiento = ComplexivoAcompanamiento.objects.get(pk=request.POST['id'])
                            grupo = acompanamiento.grupo
                            restantes = grupo.horas_restantes_fecha(f.cleaned_data['fecha'], acompanamiento.id)
                            if f.cleaned_data['horas'] > restantes:
                                return JsonResponse({'result': 'bad','mensaje': u'la cantidad de horas supera el maximo pèrmitido por día.'})

                        acompanamiento.fecha = f.cleaned_data['fecha']
                        acompanamiento.horainicio = f.cleaned_data['horainicio']
                        acompanamiento.horafin = f.cleaned_data['horafin']
                        acompanamiento.horas = f.cleaned_data['horas']
                        acompanamiento.observaciones = f.cleaned_data['observaciones']
                        acompanamiento.descripcion = f.cleaned_data['descripcion']
                        acompanamiento.enlacevideo = f.cleaned_data['enlace']
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivo_acompanamiento", newfile._name)
                            acompanamiento.archivo = newfile
                        acompanamiento.save(request)
                        log(u"Editó acompanamiento de exame complexivo %s" % acompanamiento, request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al guardar datos.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al guardar datos.'})
            elif action =='detalle_complexivo':
                try:
                    data['activo'] = ComplexivoAcompanamiento.objects.get(pk=request.POST['id'])
                    template = get_template("pro_complexivotematica/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            elif action == 'subtemas':
                try:
                    grupo = ComplexivoGrupoTematica.objects.get(pk=request.POST['id'])
                    grupo.subtema = request.POST['subtema']
                    grupo.save(request)
                    log(u"Adiciono el subtema: %s a la línea de investigación: %s" % (grupo.subtema, grupo.tematica), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

            if action == 'delete':
                try:
                    acompanamiento = ComplexivoAcompanamiento.objects.get(pk=request.POST['id'])
                    acompanamiento.status=False
                    acompanamiento.save(request)
                    log(u"Elimino acompañamiento : %s" % acompanamiento, request, "delete")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al eliminar datos.'})

            if action == 'sustentacion':
                try:
                    f = ComplexivoCalificacionSustentacionForm(request.POST, request.FILES)
                    if f.is_valid():
                        grupo = ComplexivoDetalleGrupo.objects.get(pk=request.POST['id'])
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivocalificacion_", newfile._name)
                            grupo.archivotribunal = newfile
                        # if grupo.calificacion < 70:
                        #     grupo.estado = 2
                        # else:
                        #     grupo.estado = 3
                        grupo.save(request)
                        log(u"Asentó calificación [%s] de sustentación a  %s" % ( grupo.calificacion,grupo.matricula.inscripcion), request, "add")
                        return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

            if action == 'subirurkund':
                try:
                    f = ComplexivoCalificarPropuestaForm(request.POST, request.FILES)
                    newfile = None
                    newfilec = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 12582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfile.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo Propuesta Práctica esta vacío."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc' or ext == '.docx' or ext == '.pdf':
                                    newfile._name = generar_nombre("urkund_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de Propuesta Práctica solo en .doc, docx."})
                    if 'correccion' in request.FILES:
                        newfilec = request.FILES['correccion']
                        if newfilec:
                            if newfilec.size > 12582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilec.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo Propuesta Práctica (Desde introducción hasta conclusión) esta vacío."})
                            else:
                                newfilesd = newfilec._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc' or ext == '.docx' or ext == '.pdf':
                                    newfilec._name = generar_nombre("correccion_", newfilec._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo Propuesta Práctica Antiplagio solo en .doc, docx."})
                    if f.is_valid():
                        propuesta = ComplexivoPropuestaPractica.objects.get(pk=request.POST['id'])
                        if f.cleaned_data['aprobar']:
                            archivo = ComplexivoPropuestaPracticaArchivo(propuesta=propuesta,archivo= newfile, tipo=3, fecha=datetime.now())
                            archivo.save(request)
                            log(u"Añade archivo urkund %s a revision[%s]" % (archivo, propuesta.id), request, "add")
                        else:
                            archivo = ComplexivoPropuestaPracticaArchivo(propuesta=propuesta,archivo= newfilec, tipo=4, fecha=datetime.now())
                            archivo.save(request)
                            log(u"Añade archivo de correccion %s a revision[%s]" % (archivo, propuesta.id), request, "add")
                        propuesta.fecharevision = datetime.now()
                        propuesta.observacion = f.cleaned_data['observaciones']
                        propuesta.observacion = propuesta.observacion.upper()
                        if f.cleaned_data['rechazar']:
                            propuesta.estado = 3
                        if f.cleaned_data['aprobar']:
                            propuesta.porcentajeurkund = f.cleaned_data['plagio']
                            if float(f.cleaned_data['plagio'])<= propuesta.grupo.tematica.periodo.porcentajeurkund:
                                propuesta.estado=2
                            else:
                                propuesta.estado = 3
                        if not f.cleaned_data['rechazar'] and not f.cleaned_data['aprobar']:
                            propuesta.estado = 4
                        propuesta.save(request)
                        log(u"Aprobo/Reprobo a propuesta [%s] con línea de investigación: %s" % (propuesta.id,propuesta.grupo.tematica), request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Error, ar guardar los datos.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

            if action == 'editurkund':
                try:
                    f = ComplexivoCalificarPropuestaForm(request.POST, request.FILES)
                    newfile = None
                    newfilec = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 12582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfile.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo Urkund esta vacío."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.pdf':
                                    newfile._name = generar_nombre("urkund_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo Urkund solo en pdf."})
                    if 'correccion' in request.FILES:
                        newfilec = request.FILES['correccion']
                        if newfilec:
                            if newfilec.size > 12582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilec.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo correcciones esta vacío."})
                            else:
                                newfilesd = newfilec._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc' or ext == '.docx' or ext == '.pdf':
                                    newfilec._name = generar_nombre("correccion_", newfilec._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo correcciones solo en .doc, docx, pdf."})
                    if f.is_valid():
                        propuesta = ComplexivoPropuestaPractica.objects.get(pk=request.POST['id'])
                        if newfile:
                            if propuesta.get_urkund():
                                archivo = propuesta.get_urkund()
                                archivo.archivo = newfile
                            else:
                                archivo = ComplexivoPropuestaPracticaArchivo(propuesta=propuesta, archivo=newfile, tipo=3, fecha=datetime.now())
                            archivo.save(request)
                            log(u"Añade archivo de correccion %s a revision[%s]" % (archivo, propuesta.id), request,"edit")
                        if newfilec:
                            if propuesta.get_correccion():
                                archivo = propuesta.get_correccion()
                                archivo.archivo = newfilec
                            else:
                                archivo = ComplexivoPropuestaPracticaArchivo(propuesta=propuesta, archivo=newfilec, tipo=4, fecha=datetime.now())
                            archivo.save(request)
                            log(u"Añade archivo de correccion %s a revision[%s]" % (archivo, propuesta.id), request, "edit")
                        # propuesta.porcentajeurkund = f.cleaned_data['plagio']
                        propuesta.observacion = f.cleaned_data['observaciones']
                        if f.cleaned_data['rechazar']:
                            propuesta.estado = 3
                        if f.cleaned_data['aprobar']:
                            propuesta.porcentajeurkund = f.cleaned_data['plagio']
                            if float(f.cleaned_data['plagio'])<= propuesta.grupo.tematica.periodo.porcentajeurkund:
                                propuesta.estado=2
                            else:
                                propuesta.estado = 3
                        if not f.cleaned_data['rechazar'] and not f.cleaned_data['aprobar']:
                            propuesta.estado = 4
                        propuesta.save(request)
                        log(u"Aprobo/Reprobo a propuesta [%s] con línea de investigación: %s" % (propuesta.id,propuesta.grupo.tematica), request, "add")
                        return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

            elif action == 'notas':
                try:
                    datos = json.loads(request.POST['datos'])
                    for d in datos:
                        detalle = ComplexivoExamenDetalle.objects.get(pk=d['id'])
                        detalle.calificacion = float(d['exa'])
                        detalle.calificacionrecuperacion = float(d['rec'])
                        detalle.save(True)
                        log(u"Adiciono la calificación de: %s al estudiante: %s el profesor %s" % (detalle.calificacion, detalle.matricula.inscripcion, detalle.examen.docente), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(
                        json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}), content_type="application/json")

            elif action == 'addnota_ind':
                try:
                    if 'id' in request.POST and 'not' in request.POST:
                        detalle = ComplexivoExamenDetalle.objects.get(pk=request.POST['id'], status=True)
                        detalle.calificacion = float(request.POST['not'])
                        # detalle.calificacionrecuperacion = float(request['rec'])
                        detalle.save(True)
                        log(u"Adiciono la calificación de: %s al estudiante: %s el profesor %s" % (detalle.calificacion, detalle.matricula.inscripcion, detalle.examen.docente), request, "add")
                        return JsonResponse({"result": "ok", "id":detalle.id, "estado": detalle.estado, "notafinal": round((detalle.notafinal),2)})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al Grabar la nota"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}), content_type="application/json")

            elif action == 'notasustentacion':
                try:
                    datos = json.loads(request.POST['datos'])
                    for d in datos:
                        detalle = ComplexivoDetalleGrupo.objects.get(pk=d['id'])
                        detalle.calificacion = float(d['nota'])
                        detalle.save(request)
                        detalle.actualiza_estado()
                        log(u"Adiciono calificacion: %s" % detalle, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(
                        json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}),
                        content_type="application/json")

            elif action == 'observaciones':
                try:
                    detalle = ComplexivoExamenDetalle.objects.get(pk=request.POST['id'])
                    detalle.observacion = request.POST['observacion']
                    detalle.save(request)
                    log(u"Adiciono observacion a calificacion: %s" % detalle, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

            elif action == 'editobs':
                try:
                    propuesta = ComplexivoPropuestaPractica.objects.get(pk=request.POST['id'])
                    propuesta.observacion=request.POST['observacion']
                    propuesta.observacion = propuesta.observacion.upper()
                    propuesta.save(request)
                    log(u"Edita observación a propuesta [%s] con línea de investigación: %s" % (propuesta.id,propuesta.grupo.tematica), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

            elif action == 'actacalificaciones_pdf':
                try:
                    if 'id' in request.POST:
                        data['examen'] = examen = ComplexivoExamen.objects.get(status=True, id=int(request.POST['id']))
                        data['matriculados'] = examen.complexivoexamendetalle_set.filter(status=True).order_by(
                            'matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        fecha = datetime.today().date()
                        data['xalter'] = True
                        data['fecha'] = str(fecha.day) + " de " + str(
                            MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                        data['secretariageneral'] = CargoInstitucion.objects.get(pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                        return conviert_html_to_pdf('adm_alternativatitulacion/actacalificacion_pdf.html',
                                                    {
                                                        'pagesize': 'A4',
                                                        'data': data,
                                                    }
                                                    )
                except Exception as ex:
                    pass

            elif action == 'actaacompanamiento_pdf':
                try:
                    if 'id' in request.POST:
                        data['grupo'] = grupo = ComplexivoGrupoTematica.objects.get(pk=int(request.POST['id']))
                        data['acompanamientos'] = ComplexivoAcompanamiento.objects.filter(status=True, grupo=grupo)
                        data['integrantes'] = integrantes = grupo.complexivodetallegrupo_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        valida = 0
                        for listaintegrantes in integrantes:
                            if listaintegrantes.matricula.examen_complexivo():
                                if listaintegrantes.matricula.examen_complexivo().estado == 2 and listaintegrantes.matricula.examen_complexivo().matricula.estado == 9:
                                    valida += 1
                        if integrantes.count()<=valida:
                            valida = 1
                        data['valida'] = valida
                        data['facultad'] = grupo.tematica.carrera.coordinaciones()[0]
                        fecha = datetime.today().date()
                        data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                        data['secretariageneral'] = CargoInstitucion.objects.get(pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                        return conviert_html_to_pdf('pro_complexivotematica/actaacompanamiento_pdf.html',
                                                    {
                                                        'pagesize': 'A4',
                                                        'data': data,
                                                    }
                                                    )
                except Exception as ex:
                    pass

            elif action == 'nomina_examen_pdf':
                try:
                    if 'id' in request.POST:
                        data['examen'] = examen = ComplexivoExamen.objects.get(status=True, id=int(request.POST['id']))
                        data['matriculados'] = examen.complexivoexamendetalle_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        fecha = datetime.today().date()
                        data['xalter'] = True
                        data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                        data['responsablegta'] = DistributivoPersona.objects.get(status=True, estadopuesto=1, pk=69152) if DistributivoPersona.objects.filter(status=True, estadopuesto=1, pk=69152).exists() else ''
                        return conviert_html_to_pdf('adm_alternativatitulacion/nomina_examen_pdf.html',
                                                    {
                                                        'pagesize': 'A4',
                                                        'data': data,
                                                    }
                                                    )
                except Exception as ex:
                    pass

            elif action == 'calificar_rubrica':
                try:
                    data['title'] = u'Listado de Requisitos'
                    hoy = datetime.now().date()
                    data['rubricatitulacion'] = RubricaTitulacion.objects.filter(status=True).order_by('id')
                    template = get_template("pro_complexivotematica/calificarrubrica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'aprobarcorrecion':
                try:
                    complexivotematica = ComplexivoGrupoTematica.objects.get(pk=int(request.POST['idg']))
                    complexivotematica.fechaaprobararchivofinalgrupo = datetime.now().date()
                    complexivotematica.personaprueba = persona
                    complexivotematica.estadoarchivofinalgrupo = 2
                    complexivotematica.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == 'calificar_propuesta':
                try:
                    if 'idi' in request.POST and 'idi' in request.POST:
                        data['grupointegrante'] = grupo = ComplexivoDetalleGrupo.objects.get(grupo_id=int(request.POST['idg']), pk=int(request.POST['idi']), status=True)
                        data['total'] = grupo.calificacion
                        data['persona'] = persona
                        template = get_template("pro_complexivotematica/calificarpropuesta.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al concultar los datos."})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'guardar_calificacion_propuesta':
                try:
                    if 'idi' in request.POST and 'calpresidente' in request.POST and 'calsecretaria' in request.POST and 'caldelegado' in request.POST:
                        grupointegrante = ComplexivoDetalleGrupo.objects.get(grupo_id=int(request.POST['idg']), pk=int(request.POST['idi']), status=True)
                        grupointegrante.calpresidente = float(request.POST['calpresidente'])
                        grupointegrante.calsecretaria = float(request.POST['calsecretaria'])
                        grupointegrante.caldelegado = float(request.POST['caldelegado'])
                        # calificacion = round(((float(request.POST['calpresidente'])+float(request.POST['calsecretaria'])+float(request.POST['caldelegado']))/3),2)
                        calificacion = null_to_decimal(((float(request.POST['calpresidente'])+float(request.POST['calsecretaria'])+float(request.POST['caldelegado']))/3),2)
                        grupointegrante.calificacion=calificacion
                        grupointegrante.califico = True
                        grupointegrante.save(request)
                        grupointegrante.actualiza_estado()
                        if grupointegrante.matricula.inscripcion.graduado():
                            graduado = grupointegrante.matricula.inscripcion.graduado()[0]
                            graduado.promediotitulacion=calificacion
                            graduado.save(request)
                        return JsonResponse({"result": "ok", 'calificacion': grupointegrante.calificacion})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'guardar_calificacion_sustentacion':
                try:
                    calificaciorubrica = CalificacionRubricaTitulacion.objects.get(pk=int(request.POST['id_calificacionrubrica']))
                    calificaciorubrica.confirmacalificacionrubricas = True
                    calificaciorubrica.save(request)
                    grupointegrante = ComplexivoDetalleGrupo.objects.get(pk=calificaciorubrica.complexivodetallegrupo.id, status=True)
                    if calificaciorubrica.tipojuradocalificador == 1:
                        grupointegrante.calpresidente = calificaciorubrica.puntajerubricas
                    if calificaciorubrica.tipojuradocalificador == 2:
                        grupointegrante.calsecretaria = calificaciorubrica.puntajerubricas
                    if calificaciorubrica.tipojuradocalificador == 3:
                        grupointegrante.caldelegado = calificaciorubrica.puntajerubricas
                    grupointegrante.save(request)
                    # calificacion = null_to_decimal(((float(request.POST['calpresidente'])+float(request.POST['calsecretaria'])+float(request.POST['caldelegado']))/3),2)
                    if grupointegrante.calpresidente >0 and grupointegrante.calsecretaria >0 and grupointegrante.caldelegado >0:
                        if not CalificacionRubricaTitulacion.objects.filter(complexivodetallegrupo=grupointegrante, confirmacalificacionrubricas=False, status=True):
                            valorpuntaje = CalificacionRubricaTitulacion.objects.filter(complexivodetallegrupo=grupointegrante, status=True)
                            calificacion = round(null_to_numeric(valorpuntaje.aggregate(prom=Avg('puntajerubricas'))['prom']), 2)
                            grupointegrante.calificacion = calificacion
                            grupointegrante.califico = True
                            grupointegrante.save(request)
                            grupointegrante.actualiza_estado()
                            if grupointegrante.matricula.inscripcion.graduado():
                                graduado = grupointegrante.matricula.inscripcion.graduado()[0]
                                graduado.promediotitulacion=calificacion
                                graduado.save(request)
                    return JsonResponse({"result": "ok", 'calificacion': grupointegrante.calificacion})

                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addnotasustentacion_ind':
                try:
                    if 'id' in request.POST and 'not' in request.POST:
                        detalle = ComplexivoDetalleGrupo.objects.get(pk=int(request.POST['id']), status=True)
                        detalle.calificacion = float(request.POST['not'])
                        detalle.save(request)
                        detalle.actualiza_estado()
                        log(u"Adiciono calificacion de sustentacion: %s" % detalle, request, "add")
                        return JsonResponse({"result": "ok", "id":detalle.id, "estado": detalle.matricula.estado})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al Grabar la nota"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}), content_type="application/json")

            elif action == 'updatecalificarrubricadetalle':
                try:
                    calificarricatitulacion = CalificacionRubricaTitulacion.objects.get(pk=int(request.POST['id_cabcalificarrubrica']))
                    calificarricatitulacion.confirmacalificacionrubricas = False
                    calificarricatitulacion.observacion = request.POST['id_descripcion']
                    calificarricatitulacion.save(request)
                    calificarricatitulacion.complexivodetallegrupo.califico = False
                    calificarricatitulacion.complexivodetallegrupo.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}), content_type="application/json")

            elif action == 'calificarrubricadetalle':
                try:
                    detallerubricatitulacion = CalificacionDetalleRubricaTitulacion.objects.get(pk=int(request.POST['id_calificardetallerubrica']))
                    detallerubricatitulacion.puntaje = request.POST['valornota']
                    detallerubricatitulacion.save(request)
                    detallerubricatitulacion.calificacionrubrica.confirmacalificacionrubricas = False
                    detallerubricatitulacion.calificacionrubrica.puntajerubricas = request.POST['valortotal']
                    detallerubricatitulacion.calificacionrubrica.save(request)
                    detallerubricatitulacion.calificacionrubrica.complexivodetallegrupo.califico = False
                    detallerubricatitulacion.calificacionrubrica.complexivodetallegrupo.save(request)
                    detallemodelorubrica = detallerubricatitulacion.calificacionrubrica.calificaciondetallemodelorubricatitulacion_set.filter(status=True)
                    for detalle in detallemodelorubrica:
                        detallecalificacion = CalificacionDetalleRubricaTitulacion.objects.filter(calificacionrubrica=detalle.calificacionrubrica, rubricatitulacion__modelorubrica=detalle.modelorubrica, status=True).aggregate(valor=Sum('puntaje'))['valor']
                        detalle.puntaje=detallecalificacion
                        detalle.save()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}), content_type="application/json")

            elif action == 'graduar_estudiante':
                try:
                    if 'id' in request.POST:
                        grupo = ComplexivoGrupoTematica.objects.get(pk=request.POST['id'], status=True)
                        # for detalle in grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1)| Q(matricula__estado=10))).exclude(matricula__complexivoexamendetalle__estado=2):
                        for detalle in grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1)| Q(matricula__estado=10)| Q(matricula__estado=9))):
                            if detalle.matricula.cumplerequisitos == 2 and detalle.matricula.estado == 10 and detalle.rubrica:
                                if detalle.matricula.inscripcion.completo_malla():
                                    if not detalle.matricula.inscripcion.graduado_set.filter(status=True):
                                        graduado = Graduado(inscripcion=detalle.matricula.inscripcion,
                                                            decano=None,
                                                            notafinal=0,
                                                            nombretitulo='',
                                                            horastitulacion=0,
                                                            creditotitulacion=0,
                                                            creditovinculacion=0,
                                                            creditopracticas=0,
                                                            fechagraduado= None,
                                                            horagraduacion= None,
                                                            fechaactagrado=None,
                                                            profesor=None,
                                                            integrantetribunal=None,
                                                            docentesecretario=None,
                                                            secretariageneral=None,
                                                            representanteestudiantil=None,
                                                            representantedocente=None,
                                                            representantesuplentedocente=None,
                                                            representanteservidores=None,
                                                            matriculatitulacion=None,
                                                            codigomecanismotitulacion=None,
                                                            asistentefacultad=None,
                                                            estadograduado=False,
                                                            docenteevaluador1=None,
                                                            docenteevaluador2=None,
                                                            directorcarrera=None,
                                                            tematesis='')
                                        graduado.save()
                                    if Graduado.objects.filter(Q(status=True), (Q(inscripcion=detalle.matricula.inscripcion)| Q(matriculatitulacion=detalle.matricula))).exists():
                                        graduado = Graduado.objects.get(Q(status=True), Q(inscripcion=detalle.matricula.inscripcion)| Q(matriculatitulacion=detalle.matricula))
                                        notapropuesta = float(detalle.calificacion)
                                        # record = detalle.matricula.inscripcion.promedio_record()
                                        if detalle.matricula.alternativa.tipotitulacion.tipo == 2:
                                            detalleexa = detalle.matricula.complexivoexamendetalle_set.filter(status=True, estado=3)[0]
                                            notaexamen = float(detalleexa.notafinal)
                                            notafinal = null_to_numeric(((notaexamen + notapropuesta) / 2), 2)
                                        elif detalle.matricula.alternativa.tipotitulacion.tipo == 1:
                                            notafinal = null_to_numeric((notapropuesta), 2)
                                        #     nota = null_to_numeric((notapropuesta), 2)
                                        # notafinal = null_to_numeric(((nota + record)/2), 2)
                                        graduado.promediotitulacion = notafinal
                                        graduado.estadograduado = True
                                        graduado.save(request)
                                        log(u'Graduo al estudiante: %s con nota final de: %s, cerro acta de calificación el docente: %s' % (graduado.inscripcion, str(graduado.promediotitulacion), persona), request, "grad")
                                        if detalle.matricula.alternativa.tipotitulacion.tipo == 2:
                                            if detalle.matricula.complexivoexamendetalle_set.filter(status=True, estado=3).exists():
                                                detalleexamen = detalle.matricula.complexivoexamendetalle_set.filter(status=True, estado=3)[0]
                                                adicionar_nota_complexivo(graduado.id, notapropuesta, detalleexamen.examen.fechaexamen, request)
                                            else:
                                                detalleexamen = detalle.matricula.complexivoexamendetalle_set.filter(status=True)[0]
                                                adicionar_nota_complexivo(graduado.id, notapropuesta, detalleexamen.examen.fechaexamen, request)
                                            detalle.actacerrada = True
                                            detalle.save(request)
                                            grupo.cerrado=True
                                            grupo.save(request)
                                            log(u'Cerro acta de calificación el docente: %s' % (persona), request, "edit")
                                        else:
                                            detalle.actacerrada = True
                                            detalle.save(request)
                                            grupo.cerrado = True
                                            grupo.save(request)
                                else:
                                    detalle.actacerrada = True
                                    detalle.save(request)
                                    grupo.cerrado = True
                                    grupo.save(request)
                            else:
                                detalle.califico = True
                                detalle.actacerrada = True
                                if detalle.matricula.cumplerequisitos == 3:
                                    detalle.matriculaaptahistorico = False
                                detalle.save(request)
                                detalle.matricula.estado = 9
                                detalle.matricula.save(request)
                                grupo.cerrado = True
                                grupo.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad","mensaje": u"Error al cerrar acta y graduar."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'graduar_estudiante_individual':
                try:
                    if 'id' in request.POST:
                        grupo = ComplexivoGrupoTematica.objects.get(pk=request.POST['id'], status=True)
                        # for detalle in grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1)| Q(matricula__estado=10))).exclude(matricula__complexivoexamendetalle__estado=2):
                        for detalle in grupo.complexivodetallegrupo_set.filter(Q(status=True),Q(matricula=int(encrypt(request.POST['idMat']))), (Q(matricula__estado=1) | Q(matricula__estado=10) | Q(matricula__estado=9))):
                            if detalle.matricula.cumplerequisitos == 2 and detalle.matricula.estado == 10 and detalle.rubrica:
                                if detalle.matricula.inscripcion.completo_malla():
                                    if not detalle.matricula.inscripcion.graduado_set.filter(status=True):
                                        graduado = Graduado(inscripcion=detalle.matricula.inscripcion,
                                                            decano=None,
                                                            notafinal=0,
                                                            nombretitulo='',
                                                            horastitulacion=0,
                                                            creditotitulacion=0,
                                                            creditovinculacion=0,
                                                            creditopracticas=0,
                                                            fechagraduado=None,
                                                            horagraduacion=None,
                                                            fechaactagrado=None,
                                                            profesor=None,
                                                            integrantetribunal=None,
                                                            docentesecretario=None,
                                                            secretariageneral=None,
                                                            representanteestudiantil=None,
                                                            representantedocente=None,
                                                            representantesuplentedocente=None,
                                                            representanteservidores=None,
                                                            matriculatitulacion=None,
                                                            codigomecanismotitulacion=None,
                                                            asistentefacultad=None,
                                                            estadograduado=False,
                                                            docenteevaluador1=None,
                                                            docenteevaluador2=None,
                                                            directorcarrera=None,
                                                            tematesis='')
                                        graduado.save()
                                    if Graduado.objects.filter(Q(status=True), (Q(inscripcion=detalle.matricula.inscripcion) | Q(matriculatitulacion=detalle.matricula))).exists():
                                        graduado = Graduado.objects.get(Q(status=True), Q(inscripcion=detalle.matricula.inscripcion) | Q(matriculatitulacion=detalle.matricula))
                                        notapropuesta = float(detalle.calificacion)
                                        # record = detalle.matricula.inscripcion.promedio_record()
                                        if detalle.matricula.alternativa.tipotitulacion.tipo == 2:
                                            detalleexa = detalle.matricula.complexivoexamendetalle_set.filter(status=True, estado=3)[0]
                                            notaexamen = float(detalleexa.notafinal)
                                            notafinal = null_to_numeric(((notaexamen + notapropuesta) / 2), 2)
                                        elif detalle.matricula.alternativa.tipotitulacion.tipo == 1:
                                            notafinal = null_to_numeric((notapropuesta), 2)
                                        #     nota = null_to_numeric((notapropuesta), 2)
                                        # notafinal = null_to_numeric(((nota + record)/2), 2)
                                        graduado.promediotitulacion = notafinal
                                        graduado.estadograduado = True
                                        graduado.save(request)
                                        log(u'Graduo al estudiante: %s con nota final de: %s, cerro acta de calificación el docente: %s' % (graduado.inscripcion, str(graduado.promediotitulacion), persona), request, "grad")
                                        if detalle.matricula.alternativa.tipotitulacion.tipo == 2:
                                            if detalle.matricula.complexivoexamendetalle_set.filter(status=True, estado=3).exists():
                                                detalleexamen = detalle.matricula.complexivoexamendetalle_set.filter(status=True, estado=3)[0]
                                                adicionar_nota_complexivo(graduado.id, notapropuesta, detalleexamen.examen.fechaexamen, request)
                                            else:
                                                detalleexamen = detalle.matricula.complexivoexamendetalle_set.filter(status=True)[0]
                                                adicionar_nota_complexivo(graduado.id, notapropuesta, detalleexamen.examen.fechaexamen, request)
                                            detalle.actacerrada = True
                                            detalle.save(request)
                                            grupo.cerrado = True
                                            grupo.save(request)
                                            log(u'Cerro acta de calificación el docente: %s' % (persona), request, "edit")
                                        else:
                                            detalle.actacerrada = True
                                            detalle.save(request)
                                            grupo.cerrado = True
                                            grupo.save(request)
                                else:
                                    detalle.actacerrada = True
                                    detalle.save(request)
                                    grupo.cerrado = True
                                    grupo.save(request)
                            else:
                                detalle.califico = True
                                detalle.actacerrada = True
                                if detalle.matricula.cumplerequisitos == 3:
                                    detalle.matriculaaptahistorico = False
                                detalle.save(request)
                                detalle.matricula.estado = 9
                                detalle.matricula.save(request)
                                grupo.cerrado = True
                                grupo.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al cerrar acta y graduar."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'pdfactatribunalcalificaciones':
                try:
                    data = {}
                    data['fechaactual'] = datetime.now()
                    fechainiciaactagenerar = datetime.strptime('2020-05-10', '%Y-%m-%d').date()
                    participante = ComplexivoDetalleGrupo.objects.get(pk=request.POST['id'])
                    if not participante.matricula.estado == 9:
                        if not participante.actatribunalgenerada:
                            if participante.grupo.fechadefensa > fechainiciaactagenerar:
                                participante.actatribunalgenerada = True
                                participante.numeroacta = ComplexivoDetalleGrupo.objects.filter(status=True).order_by('-numeroacta')[0].numeroacta + 1
                                participante.fechaacta = datetime.now().date()
                                participante.save(request)
                    data['participante'] = participante
                    data['detallecalificacion'] = detallecalificacion = participante.calificacionrubricatitulacion_set.filter(status=True).order_by('tipojuradocalificador')
                    data['promediopuntajetrabajointegral'] = detallecalificacion.values_list('puntajetrabajointegral').aggregate(promedio=Avg('puntajetrabajointegral'))['promedio']
                    data['promediodefensaoral'] = detallecalificacion.values_list('puntajedefensaoral').aggregate(promedio=Avg('puntajedefensaoral'))['promedio']
                    data['promediofinal'] = promediofinal = round(null_to_numeric(detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio']), 2)
                    if participante.matricula.alternativa.tipotitulacion.tipo == 2:
                        data['finalcomplexivo'] = null_to_decimal(((float(participante.notafinal()) + float(promediofinal)) / 2), 2)


                    return conviert_html_to_pdf('pro_complexivotematica/acta_calificaciontribunal_pdf.html',
                                                {
                                                    'pagesize': 'A4',
                                                    'data': data,
                                                }
                                                )
                except Exception as ex:
                    pass

            elif action == 'pdfactatribunalcalificacionesnew':
                try:
                    iddetallegrupo = request.POST['id']
                    actatribunal = actatribunalcalificacion(iddetallegrupo)
                    return actatribunal
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'pdfrubricacalificacionesnew':
                try:
                    iddetallegrupo = request.POST['id']
                    rubricatribunal = rubricatribunalcalificacion(iddetallegrupo)
                    return rubricatribunal
                except Exception as ex:
                    pass

            elif action == 'detalleobservacion':
                try:
                    listaobservaciones = []
                    listadotribunal = CalificacionRubricaTitulacion.objects.filter(complexivodetallegrupo_id=request.POST['id'], status=True)
                    for listat in listadotribunal:
                        obs = '-'
                        nomprofe = ''
                        if listat.observacion:
                            obs = listat.observacion
                        nomprofe = listat.juradocalificador.persona.apellido1 + ' ' + listat.juradocalificador.persona.apellido2 + ' ' + listat.juradocalificador.persona.nombres
                        listaobservaciones.append([nomprofe,obs,listat.get_tipojuradocalificador_display()])
                    return JsonResponse({"result": "ok", "listaobservaciones": listaobservaciones})
                except Exception as ex:
                    pass

            elif action == 'actaacompanamiento_duplicado_pdf':
                try:
                    if 'id' in request.POST:
                        grupoNuevo = ComplexivoGrupoTematica.objects.get(pk=int(request.POST['id']))
                        idmatr_grupoNuevo=ComplexivoDetalleGrupo.objects.values_list('matricula_id',flat=True).filter(status=True,grupo=grupoNuevo)
                        data['grupo'] =None
                        data['acompanamientos'] =None
                        if ComplexivoDetalleGrupo.objects.filter(status=True,matricula_id__in=idmatr_grupoNuevo,grupo__activo=False).exists():
                            detalle_grupos_grupo_antiguo=ComplexivoDetalleGrupo.objects.filter(status=True,matricula_id__in=idmatr_grupoNuevo,grupo__activo=False)
    
                            data['grupo']=detalle_grupos_grupo_antiguo[0].grupo
    
                            data['acompanamientos'] =ComplexivoAcompanamiento.objects.filter(status=True, grupo_id__in=detalle_grupos_grupo_antiguo.values_list('grupo_id',flat=True))
                        data['integrantes'] = integrantes = grupoNuevo.complexivodetallegrupo_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        valida = 0
                        for listaintegrantes in integrantes:
                            if listaintegrantes.matricula.examen_complexivo():
                                if listaintegrantes.matricula.examen_complexivo().estado == 2 and listaintegrantes.matricula.examen_complexivo().matricula.estado == 9:
                                    valida += 1
                        if integrantes.count()<=valida:
                            valida = 1
                        data['valida'] = valida
                        data['facultad'] = grupoNuevo.tematica.carrera.coordinaciones()[0]
                        fecha = datetime.today().date()
                        data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                        data['secretariageneral'] = CargoInstitucion.objects.get(pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                        return conviert_html_to_pdf('pro_complexivotematica/actaacompañamiento_duplicado_pdf.html',
                                                    {
                                                        'pagesize': 'A4',
                                                        'data': data,
                                                    }
                                                    )
                except Exception as ex:
                    pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'acompanamiento':
                try:
                    data['title']= u"Detalle Tutorías"
                    data['perid']= int(encrypt(request.GET['perid']))
                    data['grupo']= grupo = ComplexivoGrupoTematica.objects.get(pk=int(encrypt(request.GET['id'])), tematica_id=int(encrypt(request.GET['idt'])), status=True)
                    data['detalles'] = grupo.complexivoacompanamiento_set.filter(status=True).order_by('id')
                    return render(request, "pro_complexivotematica/acompanamiento.html", data)
                except Exception as ex:
                    pass

            if action == 'calificarrubricasustentacion':
                try:
                    data['title'] = u"Detalle de Calificación"
                    data['detalle'] = complexivodetallegrupo =ComplexivoDetalleGrupo.objects.get(pk=int(encrypt(request.GET['id'])), grupo_id=int(encrypt(request.GET['idg'])))
                    if complexivodetallegrupo.grupo.presidentepropuesta == profesor:
                        juradocalificador=1
                    if complexivodetallegrupo.grupo.secretariopropuesta == profesor:
                        juradocalificador=2
                    if complexivodetallegrupo.grupo.delegadopropuesta == profesor:
                        juradocalificador=3
                    data['grupo'] = complexivodetallegrupo.grupo

                    if not CalificacionRubricaTitulacion.objects.filter(complexivodetallegrupo=complexivodetallegrupo, juradocalificador=profesor, status=True):

                        calificacionrubrica = CalificacionRubricaTitulacion(complexivodetallegrupo=complexivodetallegrupo,
                                                                            observacion='',
                                                                            juradocalificador=profesor,
                                                                            tipojuradocalificador=juradocalificador,
                                                                            puntajerubricas=0)
                        calificacionrubrica.save(request)

                        rubricatitulacion = RubricaTitulacion.objects.filter(tipotitulacion=complexivodetallegrupo.matricula.alternativa.tipotitulacion.tipo, status=True).order_by('id')
                        for rub in rubricatitulacion:
                            calificaciondetallerubrica = CalificacionDetalleRubricaTitulacion(calificacionrubrica=calificacionrubrica,
                                                                                              rubricatitulacion=rub,
                                                                                              puntaje=0)
                            calificaciondetallerubrica.save(request)

                    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionRubricaTitulacion.objects.get(complexivodetallegrupo=complexivodetallegrupo, juradocalificador=profesor, status=True)
                    data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacion_set.filter(status=True).order_by('rubricatitulacion_id')
                    return render(request, 'pro_complexivotematica/calificarrubricasustentacion.html', data)
                except Exception as ex:
                    pass

            if action == 'calificarrubricasustentacionnew':
                try:
                    data['title'] = u"Detalle de Calificación"
                    data['detalle'] = complexivodetallegrupo =ComplexivoDetalleGrupo.objects.get(pk=int(encrypt(request.GET['id'])), grupo_id=int(encrypt(request.GET['idg'])))
                    if complexivodetallegrupo.grupo.presidentepropuesta == profesor:
                        juradocalificador=1
                    if complexivodetallegrupo.grupo.secretariopropuesta == profesor:
                        juradocalificador=2
                    if complexivodetallegrupo.grupo.delegadopropuesta == profesor:
                        juradocalificador=3
                    data['grupo'] = complexivodetallegrupo.grupo

                    if not CalificacionRubricaTitulacion.objects.filter(complexivodetallegrupo=complexivodetallegrupo, juradocalificador=profesor, status=True):

                        calificacionrubrica = CalificacionRubricaTitulacion(complexivodetallegrupo=complexivodetallegrupo,
                                                                            observacion='',
                                                                            juradocalificador=profesor,
                                                                            tipojuradocalificador=juradocalificador,
                                                                            puntajerubricas=0)
                        calificacionrubrica.save(request)

                        rubricatitulacion = RubricaTitulacion.objects.filter(rubrica=complexivodetallegrupo.matricula.alternativa.tipotitulacion.rubrica, status=True).order_by('id')
                        modelorubricatitulacion = ModeloRubricaTitulacion.objects.filter(rubrica=complexivodetallegrupo.matricula.alternativa.tipotitulacion.rubrica, status=True).order_by('id')
                        complexivodetallegrupo.rubrica = complexivodetallegrupo.matricula.alternativa.tipotitulacion.rubrica
                        complexivodetallegrupo.save()
                        for rubmodelo in modelorubricatitulacion:
                            calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacion(calificacionrubrica=calificacionrubrica,
                                                                                                   modelorubrica=rubmodelo,
                                                                                                   puntaje=0)
                            calificacionmodelorubrica.save(request)
                        for rub in rubricatitulacion:
                            calificaciondetallerubrica = CalificacionDetalleRubricaTitulacion(calificacionrubrica=calificacionrubrica,
                                                                                              rubricatitulacion=rub,
                                                                                              puntaje=0)
                            calificaciondetallerubrica.save(request)

                    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionRubricaTitulacion.objects.get(complexivodetallegrupo=complexivodetallegrupo, juradocalificador=profesor, status=True)
                    data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacion_set.filter(status=True).order_by('rubricatitulacion__modelorubrica__orden', 'rubricatitulacion__orden')
                    data['calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacion_set.filter(status=True).order_by('modelorubrica__orden')
                    return render(request, 'pro_complexivotematica/calificarrubricasustentacionnew.html', data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u"Añadir Registro Tutorías"
                    data['grupo']=ComplexivoGrupoTematica.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = ComplexivoAcompanamientoForm()
                    return render(request, 'pro_complexivotematica/addacompanamiento.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u"Editar Registro Acompañamiento"
                    data['detalle']=detalle = ComplexivoAcompanamiento.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupo']= detalle.grupo
                    data['form'] = ComplexivoAcompanamientoForm(initial={
                        'fecha': detalle.fecha,
                        'horainicio':detalle.horainicio.strftime('%H:%M'),
                        'horas':detalle.horas,
                        'horafin':detalle.horafin.strftime('%H:%M'),
                        'observaciones': detalle.observaciones,
                        'descripcion':detalle.descripcion,
                        'enlace': detalle.enlacevideo,
                        'archivo': detalle.archivo
                    })
                    return render(request, 'pro_complexivotematica/editacompanamiento.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u"Eliminar Registro Acompañamiento"
                    data['detalle'] = detalle = ComplexivoAcompanamiento.objects.get(pk=request.GET['id'])
                    data['grupo'] = detalle.grupo
                    return render(request, 'pro_complexivotematica/deleteacompanamiento.html', data)
                except Exception as ex:
                    pass

            if action == 'sustentacion':
                try:
                    data['title'] = u"Calificar Defensa"
                    data['idt'] = int(encrypt(request.GET['idt']))
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['profesor'] = profesor
                    fechainiciaactagenerar = datetime.strptime('2020-05-10', '%Y-%m-%d').date()
                    data['grupo'] = grupo = ComplexivoGrupoTematica.objects.get(pk=int(encrypt(request.GET['id'])), tematica_id=int(encrypt(request.GET['idt'])), status=True, activo=True)
                    puedegeneraracta = False
                    if grupo.fechadefensa > fechainiciaactagenerar:
                        puedegeneraracta = True
                    data['puedegeneraracta'] = puedegeneraracta
                    estudiante = []
                    cronogramaactivo = False
                    if 'abriracta' in request.GET:
                        for detalle in grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1) | Q(matricula__estado=10))).exclude(matricula__complexivoexamendetalle__estado=2):
                            detalle.actacerrada = False
                            detalle.save(request)
                        data['puedecalificar'] = True
                    if grupo.alternativa().get_cronograma():
                        if grupo.alternativa().get_cronograma().puede_calificar_sustentacion():
                            data['puedecalificar'] = True
                            cronogramaactivo = True
                    # if grupo.esta_graduado() and not grupo.esta_cerrar_acta_graduar():
                    if grupo.esta_graduado():
                        data['puedecalificar'] = True
                    for detalle in grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1) | Q(matricula__estado=10))).exclude(matricula__complexivoexamendetalle__estado=2):
                        if not detalle.matricula.inscripcion.completo_malla():
                            estudiante.append([detalle.matricula.inscripcion.persona.nombre_completo_inverso()])
                    data['faltamalla'] = estudiante
                    data['cronogramaactivo'] = cronogramaactivo
                    # data['integrantes'] = grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1)| Q(matricula__estado=10)| Q(matricula__estado=9))).exclude(matricula__complexivoexamendetalle__estado=2)
                    data['integrantes'] = integrantegrupo = grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1)| Q(matricula__estado=10)| Q(matricula__estado=9)))
                    puedecerraracta = False
                    if integrantegrupo.filter(actacerrada=False):
                        puedecerraracta = True
                    actacalificada = True
                    totalcumplerequisito = integrantegrupo.filter(matricula__cumplerequisitos=2).count()
                    totalactacalificada = integrantegrupo.filter(califico=True).count()
                    if totalcumplerequisito != totalactacalificada:
                        actacalificada = False
                    data['actacalificada'] = actacalificada
                    data['puedecerraracta'] = puedecerraracta
                    return render(request, 'pro_complexivotematica/calificatribunal.html', data)
                except Exception as ex:
                    pass

            if action == 'archivosustentacion':
                try:
                    data['title'] = u"Detalle de Calificación"
                    data['detalle'] = d =ComplexivoDetalleGrupo.objects.get(pk=int(encrypt(request.GET['id'])), grupo_id=int(encrypt(request.GET['idg'])))
                    data['grupo']= d.grupo
                    data['form'] = ComplexivoCalificacionSustentacionForm()
                    return render(request, 'pro_complexivotematica/sustentacion.html', data)
                except Exception as ex:
                    pass

            if action == 'subirurkund':
                try:
                    data['title'] = u"Calificar Propuesta Práctica"
                    data['propuesta'] = propuesta =ComplexivoPropuestaPractica.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupo'] = propuesta.grupo
                    data['per'] = request.GET['per']
                    form = ComplexivoCalificarPropuestaForm()
                    # propuesta.grupo.alternativa().cronogramaexamencomplexivo_set.filter(status=True).order_by('-id')[0]
                    data['form'] = form
                    return render(request, 'pro_complexivotematica/subirurkund.html', data)
                except Exception as ex:
                    pass

            if action == 'editurkund':
                try:
                    data['title'] = u"Editar trabajo de titulación"
                    data['propuesta'] = propuesta =ComplexivoPropuestaPractica.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupo'] = propuesta.grupo
                    data['per'] = request.GET['per']
                    data['form'] = ComplexivoCalificarPropuestaForm(initial={'plagio': propuesta.porcentajeurkund,
                                                                             'observaciones': propuesta.observacion,
                                                                             'aprobar': True if propuesta.estado==2 else False,
                                                                             'rechazar': True if propuesta.estado==3 else False})
                    return render(request, 'pro_complexivotematica/editurkund.html', data)
                except Exception as ex:
                    pass

            elif action == 'tomangrupo':
                try:
                    grupo = ComplexivoGrupoTematica.objects.get(pk=int(encrypt(request.GET['id'])), tematica_id=int(encrypt(request.GET['idt'])))
                    data['title'] = u'Participantes del Grupo'
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['tematica'] = grupo.tematica
                    data['participantes'] = grupo.complexivodetallegrupo_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    return render(request, 'pro_complexivotematica/tomagrupo.html', data)
                except Exception as ex:
                    pass

            elif action == 'calificaciones':
                try:
                    data['title'] = u'Examen complexivo'
                    examen = ComplexivoExamen.objects.get(pk=int(encrypt(request.GET['id'])), docente_id=int(encrypt(request.GET['idd'])))
                    data['alternativa'] = alter = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    data['examen'] = examen
                    # matriculados = examen.alternativa.matriculatitulacion_set.filter(estado=1, status=True)
                    if alter.tiene_cronogramaadicional():
                        matriculados = examen.alternativa.matriculatitulacion_set.filter(status=True, estado=9)
                    else:
                        matriculados = examen.alternativa.matriculatitulacion_set.filter(estado=1, status=True)
                    for matriculado in matriculados:
                        if not ComplexivoExamenDetalle.objects.filter(examen=examen, matricula=matriculado).exists():
                            detalle = ComplexivoExamenDetalle()
                            detalle.examen = examen
                            detalle.matricula = matriculado
                            detalle.save(request)
                    #cambio de filter
                    # data['estudiantes'] = examen.complexivoexamendetalle_set.filter(status=True).exclude(matricula__estado=8).order_by('matricula__inscripcion')
                    data['estudiantes'] = examen.complexivoexamendetalle_set.filter(status=True).order_by('matricula__inscripcion')
                    return render(request, "pro_complexivotematica/calificaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'propuesta':
                try:
                    data['title'] = u'Trabajo de titulación'
                    hoy = datetime.now().date()
                    puederevisar = False
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['grupo'] = grupo = ComplexivoGrupoTematica.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['detallecronograma'] = detallecronograma = grupo.alternativa().get_cronograma().detallerevisioncronograma_set.filter(status=True).order_by('id')
                    if detallecronograma.filter(calificacioninicio__lte=hoy, calificacionfin__gte=hoy).exists():
                        puederevisar = True
                    data['puederevisar'] = puederevisar
                    data['propuestas'] = ComplexivoPropuestaPractica.objects.filter(grupo=grupo,status=True).order_by('id')
                    return render(request, "pro_complexivotematica/propuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporte':
                grupo = ComplexivoGrupoTematica.objects.get(pk=request.GET['id'])
                acompanamientos = ComplexivoAcompanamiento.objects.filter(status=True, grupo=grupo)
                if acompanamientos.exists():
                    try:
                        __author__ = 'Unemi'
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename =NOMINA DE ACOMPAÑAMIENTO ' + '.xls'
                        normal.borders=borders
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('reporte 1')
                        ws.col(0).width = 700
                        ws.col(1).width = 4000
                        ws.col(2).width = 4000
                        ws.col(3).width = 4000
                        ws.col(4).width = 4000
                        ws.col(5).width = 8000

                        integrantes= ComplexivoDetalleGrupo.objects.filter(status=True,grupo=grupo.id)
                        ws.write_merge(1, 1, 0, 5, u'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        tiem = datetime.today().date()
                        ws.write(2, 0, 'Milagro, ' + str(tiem), nnormal)
                        ws.merge(2, 2, 0, 5)
                        ws.write_merge(3, 3, 0, 5, u'REGISTRO DE ACOMPAÑAMIENTOS ', title)
                        ws.write(4,0,u'INICIO: %s'%(grupo.tematica.periodo.fechainicio)+u' FIN: %s'%(grupo.tematica.periodo.fechafin),subtitle )
                        ws.merge(4,4,0,5,subtitle)
                        ws.write(5, 0, u'%s'%(grupo.tematica.carrera.coordinaciones()[0]), stylebnombre)
                        ws.merge(5, 5, 0, 5, stylebnombre)
                        ws.write(6, 0, u'CARRERA: %s' % grupo.tematica.carrera.nombre, stylebnombre)
                        ws.merge(6, 6, 0, 5, stylebnombre)
                        ws.write(7,0, u'Línea de investigación: %s' % grupo.tematica.tematica.tema, stylebnombre)
                        ws.merge(7,7,0,5,stylebnombre)
                        ws.write(8,0, u'TEMA: %s'%(grupo.subtema), stylebnombre)
                        ws.merge(8,8,0,5,stylebnombre)
                        ws.write(9,0, u'ACOMPAÑANTE:%s' %(grupo.tematica.tutor), stylebnombre)
                        ws.merge(9,9,0,5,stylebnombre)
                        ws.write_merge(11, 11, 0, 5, u'DATOS DEL ESTUDIANTE', stylebnotas)
                        ws.write_merge(12, 12, 0, 0, u'Nº:', stylebnotas)
                        ws.write_merge(12, 12, 1, 3, u'APELLIDOS Y NOMBRES:', stylebnotas)
                        ws.write_merge(12, 12, 4, 4, u'CÉDULA', stylebnotas)
                        ws.write_merge(12, 12, 5, 5, u'CARRERA:', stylebnotas)
                        j = 1
                        encabezado = 13
                        for integrante in integrantes:
                            ws.write(encabezado, 0, str(j), normal)
                            ws.write(encabezado, 1, str(integrante.matricula.inscripcion), normal)
                            ws.merge(encabezado,encabezado,1,3,normal)
                            ws.write(encabezado, 4, str(integrante.matricula.inscripcion.persona.cedula), normal)
                            ws.write(encabezado, 5, str(integrante.matricula.inscripcion.carrera), normal)
                            j=j+1
                            encabezado=encabezado+1
                        encabezado=encabezado+1
                        ws.write(encabezado, 0, 'Nº', stylebnotas)
                        ws.write(encabezado, 1, 'FECHA', stylebnotas)
                        ws.write_merge(encabezado, encabezado,2,3, 'HORA', stylebnotas)
                        ws.write(encabezado, 4, 'Nº HORAS', stylebnotas)
                        ws.write(encabezado, 5, 'DETALLE', stylebnotas)
                        fil = encabezado + 1
                        i = 1
                        for acompanamiento in acompanamientos:
                            ws.write(fil, 0,str(i), normal)
                            ws.write(fil, 1,str(acompanamiento.fecha), normal)
                            ws.write(fil, 2,u'Inicio: %s' %(acompanamiento.horainicio), normal)
                            ws.write(fil, 3,u'Fin: %s' %(acompanamiento.horafin), normal)
                            ws.write(fil, 4,str(acompanamiento.horas), normal)
                            obser=u""+acompanamiento.observaciones
                            ws.write(fil, 5,u''+obser.capitalize(), normaliz)
                            fil=fil+1
                            i=i+1
                        ws.write_merge(fil + 5, fil + 5, 0, 2, '_______________________________________', subtitle)
                        ws.write(fil + 6, 0, u'%s' %(grupo.tematica.tutor), subtitle)
                        ws.merge(fil + 6, fil + 6, 0, 2)
                        ws.write_merge(fil + 7, fil + 7, 0, 2, 'PROFESOR', subtitle)
                        ws.write_merge(fil + 5, fil + 5, 5, 5, '_______________________________________', subtitle)
                        ws.write_merge(fil + 6, fil + 6, 5, 5, u'%s' %(grupo.tematica.director), subtitle)
                        ws.write_merge(fil + 7, fil + 7, 5, 5, u'DIRECTOR(A) DE CARRERA', subtitle)
                        fil=fil+15
                        col1=0
                        col2=2
                        for integrante in integrantes:
                            ws.write_merge(fil, fil , col1, col2, '_______________________________________', subtitle)
                            ws.write(fil+1, col1, u'%s' % (integrante.matricula.inscripcion), subtitle)
                            ws.merge(fil+1, fil+1,col1,col2)
                            ws.write_merge(fil+2, fil+2, col1, col2, u'ESTUDIANTE', subtitle)
                            col1=5
                            col2=5
                        wb.save(response)
                        return response
                    except Exception as es:
                        pass

            elif action == 'cerraracta':
                try:
                    data['title'] = u'Cerrar acta tribunal calificador'
                    data['idt'] = int(encrypt(request.GET['idt']))
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['grupo'] = grupo = ComplexivoGrupoTematica.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['detalles'] = grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1)| Q(matricula__estado=10)| Q(matricula__estado=9)), matricula__cumplerequisitos=2,rubrica__isnull=False).exclude(matricula__complexivoexamendetalle__estado=2)
                    return render(request, "pro_complexivotematica/cerrar_acta.html", data)
                except Exception as ex:
                    pass

            elif action == 'cerraracta_individual':
                try:
                    data['title'] = u'Cerrar acta tribunal calificador'
                    data['idt'] = int(encrypt(request.GET['idt']))
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['idMat'] = request.GET['idMat']
                    data['grupo'] = grupo = ComplexivoGrupoTematica.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['detalles'] = grupo.complexivodetallegrupo_set.filter(Q(status=True),Q(matricula=int(encrypt(request.GET['idMat']))), (Q(matricula__estado=1)| Q(matricula__estado=10)| Q(matricula__estado=9)), matricula__cumplerequisitos=2,rubrica__isnull=False).exclude(matricula__complexivoexamendetalle__estado=2)
                    return render(request, "pro_complexivotematica/cerrar_acta_individual.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u"Grupo de línea de investigación"
                periodotitulacion = int(encrypt(request.GET['per'])) if 'per' in request.GET else 0
                data['archivos'] = ArchivoTitulacion.objects.filter(vigente=True, tipotitulacion__tipo=2)
                data['titperiodos'] = periodos = PeriodoGrupoTitulacion.objects.filter(status=True).order_by('-fechainicio')
                grupos = ComplexivoGrupoTematica.objects.filter(activo=True,status=True, tematica__tutor__participante__persona__id=persona.id).order_by('tematica__tematica__tema')
                grs = ComplexivoGrupoTematica.objects.filter(Q(status=True), Q(presidentepropuesta__persona=persona)| Q(secretariopropuesta__persona=persona) | Q(delegadopropuesta__persona=persona),activo=True).order_by('-fechadefensa', '-horadefensa')
                examenes = ComplexivoExamen.objects.filter(docente=profesor, alternativa__status=True).order_by('-fechaexamen')
                data['perid'] = periodos.order_by('-id')[0]
                data['docente'] = profesor
                if periodotitulacion > 0:
                    data['perid'] = PeriodoGrupoTitulacion.objects.get(pk=periodotitulacion)
                    grupos = grupos.filter(tematica__periodo_id=periodotitulacion)
                    grs = grs.filter(tematica__periodo_id=periodotitulacion)
                    examenes = examenes.filter(alternativa__grupotitulacion__periodogrupo_id = periodotitulacion, alternativa__status=True)
                else:
                    data['perid'] = periodos.order_by('-id')[0]
                    grupos = grupos.filter(tematica__periodo=periodos.order_by('-id')[0])
                    grs = grs.filter(tematica__periodo=periodos.order_by('-id')[0])
                    examenes = examenes.filter(alternativa__grupotitulacion__periodogrupo=periodos.order_by('-id')[0], alternativa__status=True)
                grupossustentacion = []
                for gr in grs:
                    if gr.tiene_propuesta_aceptada():
                        grupossustentacion.append(gr)
                data['grupos'] = grupos
                data['grupossustentacion'] = grupossustentacion
                data['examenes'] = examenes
                return render(request, "pro_complexivotematica/view.html", data)
            except Exception as ex:
                pass
def adicionar_nota_complexivo(idgraduado, nota, fecha, request):
    if ExamenComlexivoGraduados.objects.filter(graduado_id=idgraduado, itemexamencomplexivo_id=2).exists():
        itendetalle = ExamenComlexivoGraduados.objects.get(graduado_id=idgraduado, itemexamencomplexivo_id=2)
        itendetalle.examen = nota
        itendetalle.ponderacion = null_to_decimal((nota / 2), 2)
        itendetalle.fecha = fecha
        log(u'Adicionó Examen Complexivo graduado: %s' % itendetalle, request, "edit")
    else:
        itendetalle = ExamenComlexivoGraduados(graduado_id=idgraduado,
                                               itemexamencomplexivo_id=2,
                                               examen=nota,
                                               ponderacion=null_to_decimal((nota / 2), 2),
                                               fecha=fecha
                                               )
        log(u'Adicionó Examen Complexivo graduado por tribunal: %s' % itendetalle, request, "add")
    itendetalle.save(request)