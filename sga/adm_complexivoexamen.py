# -*- coding: UTF-8 -*-
from datetime import *
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import *
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ComplexivoExamenForm, ComplexivoCalificacionDiaForm
from sga.funciones import log
from sga.models import AlternativaTitulacion, ComplexivoExamen, ComplexivoExamenDetalle, CronogramaExamenComplexivo, \
    MatriculaTitulacion

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
@last_access

def view(request):
    data = {}
    adduserdata(request, data)
    # bordes
    borders = Borders()
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1
    # estilos para los reportes
    title = easyxf('font: name Arial, bold on , height 200; alignment: horiz centre')
    subtitle = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    peque = easyxf('font: name Arial, bold on , height 125; alignment: horiz left')
    nnormal = easyxf('font: name Arial, bold on , height 150; alignment: horiz left')
    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
    stylenotas = easyxf('font: name Arial , height 150; alignment: horiz centre')
    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    stylebnombre = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    stylevacio = easyxf('font: name Arial , height 600; alignment: horiz centre')
    normal.borders = borders
    stylebnotas.borders = borders
    stylenotas.borders = borders
    stylebnombre.borders = borders
    stylevacio.borders = borders

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add' or action == 'edit':
            try:
                f  = ComplexivoExamenForm(request.POST)
                if f.is_valid():
                    exa = f.cleaned_data['fechaexamen']
                    gra = f.cleaned_data['fechaexamenrecuperacion']

                    cro = CronogramaExamenComplexivo.objects.get(alternativatitulacion=request.POST['alternativa'])
                    if exa < cro.fechaaprobexameninicio or exa > cro.fechaaprobexamenfin:
                        return JsonResponse({'result': 'bad','mensaje': u"Fechas no estan acorde al cronograma"})
                    if exa > gra :
                        return JsonResponse({'result':'bad', 'mensaje':u"Fecha de examen de gracia no debe ser menor a la fecha de Examen complexivo"})

                    if action == 'add':
                        examen= ComplexivoExamen()
                        examen.alternativa_id = request.POST['alternativa']
                    else:
                        examen= ComplexivoExamen.objects.get(pk=request.POST['id'])
                    examen.aula = f.cleaned_data['aula']
                    examen.fechaexamen = f.cleaned_data['fechaexamen']
                    examen.docente=f.cleaned_data['profesor']
                    examen.notaminima = f.cleaned_data['notaminima']
                    examen.horainicio = f.cleaned_data['horainicio']
                    examen.horafin = f.cleaned_data['horafin']
                    examen.horainiciorecuperacion= f.cleaned_data['horainiciorecuperacion']
                    examen.horafinrecuperacion = f.cleaned_data['horafinrecuperacion']
                    examen.fechaexamenrecuperacion = f.cleaned_data['fechaexamenrecuperacion']
                    examen.save(request)
                    if action == 'add':
                        log(u"Adiciono examen: %s" % examen, request, "add")
                        matriculados = examen.alternativa.matriculatitulacion_set.filter(estado=1)
                        for matriculado in matriculados:
                            detalle = ComplexivoExamenDetalle()
                            detalle.examen=examen
                            detalle.matricula = matriculado
                            detalle.save(request)
                    else:
                        log(u"Edito examen: %s" % examen, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        if action == 'delete':
            try:
                examen = ComplexivoExamen.objects.get(pk=request.POST['id'])
                if not examen.tiene_examen():
                    examen.status = False
                    examen.save(request)
                    log(u"Elimino examen: %s" % examen, request, "delete")
                    return JsonResponse({"result": "ok", "id": examen.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya se asignado calificaciones"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex})
        if action == 'diasacalificar':
            try:
                examen = ComplexivoExamen.objects.get(pk=request.POST['id'])
                form = ComplexivoCalificacionDiaForm(request.POST)
                if form.is_valid():
                    examen.usacronograma = form.cleaned_data['usacronograma']
                    examen.diascalificar = form.cleaned_data['diasacalificar'] if form.cleaned_data['diasacalificar'] else 1
                    examen.save(request)
                    log(u'Cambio en fecha de calificaciones de examen: %s' % examen, request, "edit")
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
            if action == 'add':
                try:
                    data['title'] = u"Añadir Examen Complexivo"
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=request.GET['alt'])
                    data['form']=ComplexivoExamenForm()
                    return render(request, "adm_complexivoexamen/add.html", data)
                except Exception as ex:
                    pass
            elif action == 'edit':
                try:
                    data['title'] = u"Editar Examen Complexivo"
                    data['examen']=examen=ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    data['form']=ComplexivoExamenForm(initial={
                        'profesor':examen.docente,
                        'aula':examen.aula,
                        'horainicio':str(examen.horainicio),
                        'horafin':str(examen.horafin),
                        'notaminima': examen.notaminima,
                        'fechaexamen':examen.fechaexamen,
                        'horainiciorecuperacion': str(examen.horainiciorecuperacion),
                        'horafinrecuperacion': str(examen.horafinrecuperacion),
                        'fechaexamenrecuperacion': examen.fechaexamenrecuperacion
                    })
                    return render(request, "adm_complexivoexamen/edit.html", data)
                except Exception as ex:
                    pass
            elif action == 'delete':
                try:
                    data['examen'] =  examen = ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['title'] = u'Eliminar examen'
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    return render(request, "adm_complexivoexamen/del.html", data)
                except Exception as ex:
                    pass

            elif action == 'diasacalificar':
                try:
                    data['title'] = u'Dias para calificar'
                    examen = ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    data['examen'] = examen
                    data['form'] = ComplexivoCalificacionDiaForm(initial={
                        'usacronograma' : examen.usacronograma,
                        'diasacalificar' : examen.diascalificar
                    })
                    return render(request, "adm_complexivoexamen/diasacalificar.html", data)
                except Exception as ex:
                    pass
            elif action == 'prueba':
                try:
                    examen = ComplexivoExamen.objects.get(status=True, id=int(request.GET['id']))
                    opcion = request.GET['opcion']
                    if opcion == 'actaexamen' or opcion == 'nominaexamen':
                        if ComplexivoExamenDetalle.objects.filter(examen=examen.id).exists():
                            return JsonResponse({"result": "ok"})
                    elif ComplexivoExamenDetalle.objects.filter(examen=examen.id,calificacion__lt=examen.notaminima).exists():
                        return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "bad", "mensaje": "No existen alumnos para este reporte"})
                except Exception as ex:
                    pass

            elif action == 'calificaciones':
                try:
                    data['title'] = u'Examen complexivo'
                    examen = ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    data['examen'] = examen
                    data['estudiantes'] = examen.complexivoexamendetalle_set.all().order_by(
                        'matricula__inscripcion')
                    return render(request, "adm_complexivoexamen/calificaciones.html", data)
                except Exception as ex:
                    pass
            elif action == 'actaexamen': #or action == 'actapropuesta'
                try:
                    examen = ComplexivoExamen.objects.get(status=True, id=int(request.GET['id']))
                    __author__ = 'Unemi'
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte 1')
                    # hoja
                    ws.write_merge(1, 1, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(2, 2, 0, 8, 'VICERRECTORADO ACADÉMICO Y DE INVESTIGACIÓN', title)
                    ws.write_merge(3, 3, 0, 8, 'GESTIÓN TÉCNICA ACADÉMICA', title)
                    ws.write_merge(4, 4, 0, 8, 'PROCESO DE  TITULACIÓN', title)
                    ws.write_merge(5, 5, 0, 8, 'ACTA DE CALIFICACIÓN', subtitle)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename =ACTA DE CALIFICACIONES ' + '.xls'
                    ws.col(0).width = 1000
                    ws.col(1).width = 5000
                    ws.col(2).width = 5000
                    ws.col(3).width = 2500
                    ws.col(4).width = 1300
                    ws.col(5).width = 1300
                    ws.col(6).width = 1500
                    ws.col(7).width = 1400

                    ws.write(6, 0, 'PERIODO: ' + str(examen.alternativa.grupotitulacion.periodogrupo.nombre),
                             subtitle)
                    ws.merge(6, 6, 0, 8)
                    ws.write(7, 0, 'INICIO: ' + str(examen.alternativa.grupotitulacion.fechainicio) +
                                   ' FIN: ' + str(examen.alternativa.grupotitulacion.fechafin), subtitle)
                    ws.merge(7, 7, 0, 8)
                    ws.write(9, 0, str(examen.alternativa.facultad), nnormal)
                    ws.merge(9, 9, 0, 2)
                    ws.write(12, 3, 'EXAMEN COMPLEXIVO: '+str(examen.fechaexamen), nnormal)
                    ws.merge(12, 12, 3, 8)
                    ws.write(13, 3, 'EXAMEN GRACIA: '+str(examen.fechaexamenrecuperacion), nnormal)
                    ws.merge(13, 13, 3, 8)
                    ws.write(10, 0, 'CARRERA: ' + str(examen.alternativa.carrera), nnormal)
                    ws.merge(10, 10, 0, 8)
                    ws.write(11, 0, 'ALTERNATIVA DE TITULACIÓN: ' + str(examen.alternativa), nnormal)
                    ws.merge(11, 11, 0, 8)
                    ws.write(12, 0, 'PROFESOR: ' + str(examen.docente), nnormal)
                    ws.merge(12, 12, 0, 2)
                    ws.write(13, 0, 'PARALELO: ' + str(examen.alternativa.paralelo), nnormal)
                    ws.merge(13, 13, 0, 2)
                    tiem= datetime.today().date()
                    ws.write(8, 0, 'Milagro, '+str(tiem), nnormal)
                    ws.merge(8, 8,0 , 7)
                    # LETRAS PEQUEÑAS
                    ws.write_merge(15,15,3,4, 'EX1(COMPLEXIVO)', peque)
                    ws.write_merge(16,16,3,4, 'EX2(GRACIA)', peque)
                    ws.write_merge(15,15,5,7, 'N.FINAL(NOTA FINAL)', peque)
                    ws.write_merge(16,16,5,7, 'POND(PONDERACION)', peque)
                    # cuadro
                    ws.write_merge(15,15,0,1, 'Evaluaciones Parciales', stylenotas)
                    ws.write_merge(16,17,0,1, 'De: 1-100', stylenotas)


                    encabezado=19
                    ws.write(encabezado, 0, 'Nº', stylebnotas)
                    ws.write_merge(encabezado,encabezado, 1,2, 'APELLIDOS Y NOMBRES', stylebnombre)
                    # ws.write(encabezado, 3, 'CÉDULA', stylebnotas)
                    ws.write(encabezado, 4, 'EX1', stylebnotas)
                    ws.write(encabezado, 5, 'EX2', stylebnotas)
                    ws.write(encabezado, 6, 'N.FINAL', stylebnotas)
                    ws.write(encabezado, 7, 'POND', stylebnotas)
                    ws.write(encabezado, 8, 'ESTADO', stylebnotas)
                    # if action =='actapropuesta':
                    #     # propuesta=Co

                    listamatriculados = ComplexivoExamenDetalle.objects.filter(examen=examen.id).order_by('matricula__inscripcion__persona__apellido1')

                    if listamatriculados.exists():
                        i = 0
                        for matriculados in listamatriculados:
                            fil = i + 20
                            ws.write(fil, 0, str(i + 1), stylenotas)
                            ws.write(fil, 1, str(matriculados.matricula), normal)
                            ws.merge(fil, fil, 1, 2,normal)
                            # ws.write(fil, 3, str(matriculados.matricula.inscripcion.persona.cedula), stylenotas)
                            ws.write(fil, 4, str(matriculados.calificacion), stylenotas)
                            ws.write(fil, 5, str(matriculados.calificacionrecuperacion), stylenotas)
                            ws.write(fil, 6, str(matriculados.notafinal), stylenotas)
                            ws.write(fil, 7, str((matriculados.notafinal*50)/100), stylenotas)

                            if matriculados.notafinal >= examen.notaminima:
                                estado = 'APROBADO'
                            else:
                                estado = 'REPROBADO'
                            ws.write(fil, 8, str(estado), stylenotas)
                            i = i + 1
                        # ws.write_merge(fil+2,fil+2,0,8,"Observación: _________________________________________________________________________",nnormal)
                        ws.write_merge(fil+5,fil+5,0,2,'_______________________________________',subtitle)
                        ws.write(fil+6,0,str(examen.docente),subtitle)
                        ws.merge(fil+6,fil+6,0,2)
                        ws.write_merge(fil+7, fil+7,0,2,'PROFESOR',subtitle)
                        ws.write_merge(fil+5, fil+5,3,8, '_______________________________________', subtitle)
                        ws.write_merge(fil+6, fil+6,3,8,'LIC. DIANA MARYLYN PINCAY CANTILLO',subtitle)
                        ws.write_merge(fil+7, fil+7,3,8,'SECRETARÍA GENERAL',subtitle)
                        # ws.write_merge(fil+10,fil+10,2,7, '_______________________________________', subtitle)
                        # ws.write_merge(fil+11,fil+11,2,7,'ING. VIVIANA GAIBOR HINOSTROZA,MSC',subtitle)
                        # ws.write_merge(fil+12,fil+12,2,7,'GESTIÓN TÉCNICA ACADÉMICA',subtitle)
                        ws.write_merge(fil+10,fil+10,0,1, 'Recepción: Mes:     Día:     Hora:', peque)
                        ws.write_merge(fil+12,fil+12,0,1, '_______________________________________', peque)
                        ws.write_merge(fil+13,fil+13,0,1, 'Secretaria Responsable:', peque)
                        ws.write_merge(fil+15,fil+15,0,1, '_______________________________________', peque)
                        wb.save(response)
                        return response

                except Exception as es:
                    pass
            elif action == 'eliminaciontotal':
                try:
                     exramatri = MatriculaTitulacion.objects.exclude(estado=1)
                     ComplexivoExamenDetalle.objects.filter(matricula__in = exramatri).delete()
                     return HttpResponseRedirect("/adm_alternativatitulacion")
                except Exception as ex:
                    transaction.set_rollback(True)

            elif action == 'nominaexamen' or action == 'nominagracia':
                try:
                    examen = ComplexivoExamen.objects.get(status=True, id=int(request.GET['id']))
                    matriculados = examen.alternativa.matriculatitulacion_set.filter(estado=1)

                    __author__ = 'Unemi'
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte 1')
                    # hoja
                    if action == 'nominaexamen':
                        nombre='NÓMINA DE EXAMEN COMPLEXIVO'
                        exa='EXAMEN COMPLEXIVO'
                        fecha=examen.fechaexamen

                        listamatriculados = ComplexivoExamenDetalle.objects.filter(examen=examen.id).order_by(
                            'matricula__inscripcion__persona__apellido1')
                    else:
                        nombre = 'NÓMINA DE EXAMEN DE GRACIA'
                        exa='EXAMEN DE GRACIA'
                        fecha=examen.fechaexamenrecuperacion
                        listamatriculados = ComplexivoExamenDetalle.objects.filter(examen=examen.id, calificacion__lt=examen.notaminima).order_by(
                            'matricula__inscripcion__persona__apellido1')
                    if listamatriculados.exists():

                        ws.write_merge(1, 1, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write_merge(2, 2, 0, 4, 'VICERRECTORADO ACADÉMICO Y DE INVESTIGACIÓN', title)
                        ws.write_merge(3, 3, 0, 4, 'GESTIÓN TÉCNICA ACADÉMICA', title)
                        ws.write_merge(4, 4, 0, 4, 'PROCESO DE  TITULACIÓN', title)
                        ws.write(5, 0, str(nombre), subtitle)
                        ws.merge(5, 5, 0, 4)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename = NOMINA DE ESTUDIANTES ' + '.xls'
                        ws.col(0).width = 1000
                        ws.col(1).width = 10000
                        ws.col(2).width = 2500
                        ws.col(3).width = 4000
                        ws.col(4).width = 4000
                        ws.col(5).width = 1500
                        ws.col(6).width = 1300
                        ws.write(6, 0, 'PERIODO: ' + str(examen.alternativa.grupotitulacion.periodogrupo.nombre),
                                 subtitle)
                        ws.merge(6, 6, 0, 4)
                        ws.write(7, 0, 'INICIO: ' + str(examen.alternativa.grupotitulacion.fechainicio) +
                                 ' FIN: ' + str(examen.alternativa.grupotitulacion.fechafin), subtitle)
                        ws.merge(7, 7, 0, 4)
                        ws.write(9, 0, str(examen.alternativa.facultad), nnormal)
                        ws.merge(9, 9, 0, 1)
                        ws.write(12, 3, 'EXAMEN:'+ exa, nnormal)
                        ws.merge(12, 12, 3, 4)
                        ws.write(13, 3, 'FECHA EXAMEN:'+ str(fecha), nnormal)
                        ws.merge(13, 13, 3, 4)
                        ws.write(13, 0, 'PARALELO: '+ str(examen.alternativa.paralelo), nnormal)
                        ws.merge(13,13,0,2)
                        ws.write(10, 0, 'CARRERA: ' + str(examen.alternativa.carrera), nnormal)
                        ws.merge(10, 10, 0, 4)
                        ws.write(11, 0, 'ALTERNATIVA DE TITULACIÓN: ' + str(examen.alternativa), nnormal)
                        ws.merge(11, 11, 0, 4)
                        ws.write(12, 0, 'PROFESOR: ' + str(examen.docente), nnormal)
                        ws.merge(12, 12, 0, 2)
                        tiem = datetime.today().date()
                        ws.write(8, 0, 'Milagro, ' + str(tiem), nnormal)
                        ws.merge(8, 8, 0, 4)
                        encabezado = 15
                        ws.write(encabezado, 0, 'Nº', stylebnotas)
                        ws.write(encabezado, 1, 'APELLIDOS Y NOMBRES', stylebnombre)
                        ws.write(encabezado, 2, 'CÉDULA', stylebnotas)
                        ws.write(encabezado, 3, 'FIRMA', stylebnotas)
                        ws.write(encabezado, 4, 'OBSERVACIONES', stylebnotas)
                        i = 0
                        for matriculados in listamatriculados:
                            fil = i + 16
                            ws.write(fil, 0, str(i + 1), stylenotas)
                            ws.write(fil, 1, str(matriculados.matricula), normal)
                            ws.write(fil, 2, str(matriculados.matricula.inscripcion.persona.cedula), stylenotas)
                            ws.write(fil, 3, ' ', stylevacio)
                            ws.write(fil, 4, ' ', stylevacio)
                            i = i + 1
                        ws.write_merge(fil + 2, fil + 2, 0, 4,
                                       "Observación: _________________________________________________________________________",
                                       nnormal)
                        ws.write_merge(fil + 5, fil + 5, 0, 1, '_______________________________________', subtitle)
                        ws.write(fil + 6, 0, str(examen.docente), subtitle)
                        ws.merge(fil + 6, fil + 6, 0, 1)
                        ws.write_merge(fil + 7, fil + 7, 0, 1, 'PROFESOR', subtitle)
                        ws.write_merge(fil + 5, fil + 5, 2, 4, '_______________________________________', subtitle)
                        ws.write_merge(fil + 6, fil + 6, 2, 4, 'ING. VIVIANA GAIBOR HINOSTROZA,MSC', subtitle)
                        ws.write_merge(fil + 7, fil + 7, 2, 4, u'PROCESO DE TITULACIÓN', subtitle)
                        ws.write_merge(fil + 8, fil + 8, 2, 4, u'GESTIÓN TÉCNICA ACADÉMICA', subtitle)
                        ws.write_merge(fil + 10, fil + 10, 0, 1, 'Recepción: Mes:   Día:    Hora:', peque)
                        ws.write_merge(fil + 12, fil + 12, 0, 1, '_______________________________________', peque)
                        ws.write_merge(fil + 13, fil + 13, 0, 1, 'Secretaria Responsable:', peque)
                        ws.write_merge(fil + 15, fil + 15, 0, 1, '_______________________________________', peque)
                        wb.save(response)
                        return response

                except Exception as es:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Examen Complexivo'
            data['alternativa'] = alternativa =AlternativaTitulacion.objects.get(pk=request.GET['alt'])
            data['examenes'] = alternativa.complexivoexamen_set.filter(status=True)
            return render(request, "adm_complexivoexamen/view.html", data)
