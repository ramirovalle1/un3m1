from builtins import int
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.models import CapInstructorIpec, CapDetalleNotaIpec, CapInscritoIpec, CapEventoPeriodoIpec,CapModeloEvaluativoTareaIpec,CapNotaIpec
from sga.commonviews import adduserdata, actualizar_nota_instructor
from sga.funciones import log, MiPaginador, null_to_decimal
from xlwt import *
from xlwt import easyxf
import xlwt
import random

from sga.templatetags.sga_extras import encrypt

unicode = str

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if not CapInstructorIpec.objects.values("id").filter(instructor=persona):
        return HttpResponseRedirect("/?info=Solo los instructores pueden ingresar al modulo.")
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addnota':
                try:
                    notaanterior = ''
                    if CapDetalleNotaIpec.objects.filter(cabeceranota_id=int(request.POST['idm']), inscrito_id=int(request.POST['ida']), cabeceranota__instructor__capeventoperiodo_id=int(request.POST['ide'])).exists():
                        detalle = CapDetalleNotaIpec.objects.get(cabeceranota_id=int(request.POST['idm']), inscrito_id=int(request.POST['ida']), cabeceranota__instructor__capeventoperiodo_id=int(request.POST['ide']))
                        nota = float(request.POST['nota'])
                        if not nota:
                            nota = None
                        notaanterior = detalle.nota
                        detalle.nota = nota
                    else:
                        detalle = CapDetalleNotaIpec(cabeceranota_id=int(request.POST['idm']), inscrito_id=int(request.POST['ida']), nota=float(request.POST['nota']))
                    detalle.save(request)
                    instructor = detalle.cabeceranota.instructor
                    evento = detalle.cabeceranota.instructor.capeventoperiodo
                    log(u'Actualizo nota en tarea de capacitacion IPEC: %s nota anterior: %s nota actualizada: %s del modelo de evaluativo %s' % (detalle, str(notaanterior), str(detalle.nota), detalle.cabeceranota.modelo), request, "edit")
                    # return JsonResponse({'result': 'ok', 'total': detalle.inscrito.nota_total_evento(int(request.POST['ide']))})
                    nofinal = detalle.inscrito.nota_total_evento_porinstructor(evento.id, instructor.pk)

                    return JsonResponse({'result': 'ok', 'total': nofinal})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar la nota."})

            elif action == 'addobservacion':
                try:
                    inscrito = CapInscritoIpec.objects.get(capeventoperiodo_id=int(request.POST['ide']), id=int(request.POST['id']))
                    inscrito.observacion = request.POST['obs']
                    inscrito.save(request)
                    log(u'Actualizo observación: %s de capacitacion IPEC: %s ' % (inscrito.observacion, inscrito.capeventoperiodo), request, "edit")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar la nota."})

            elif action == 'extraernotasmoodle':
                try:
                    instructor = CapInstructorIpec.objects.get(pk=request.POST['id'], status=True)
                    evento = instructor.capeventoperiodo
                    for alumno in evento.list_inscritos_sin_costo_2():
                        # Extraer datos de moodle
                        for notasmooc in instructor.notas_de_moodle(alumno.participante):
                            # campo=None
                            # if type(notasmooc[0]) is Decimal:
                            #     campo = alumno.campo(notasmooc[1].upper(),instructor.id)
                            #     if campo:
                            #         if null_to_decimal(campo[1]) != float(notasmooc[0]):
                            #             actualizar_nota_instructor(alumno.id, notasmooc[1].upper(), notasmooc[0],instructor.id,request)
                            # else:
                            #     actualizar_nota_instructor(alumno.id, notasmooc[1].upper(), notasmooc[0],instructor.id,request)
                            if type(notasmooc[0]) is Decimal:
                                if CapNotaIpec.objects.filter(status=True,instructor=instructor,modelo__nombre=notasmooc[1].upper()).exists():
                                    modeloevaluativo= CapNotaIpec.objects.filter(status=True,instructor=instructor,modelo__nombre=notasmooc[1].upper() )
                                    notaanterior=0
                                    if CapDetalleNotaIpec.objects.filter(status=True, cabeceranota__status=True, cabeceranota_id=modeloevaluativo[0],
                                                                         inscrito=alumno,
                                                                         cabeceranota__instructor__capeventoperiodo=instructor.capeventoperiodo,
                                                                         cabeceranota__instructor=instructor).exists():
                                        detalle = CapDetalleNotaIpec.objects.filter(status=True, cabeceranota__status=True, cabeceranota_id=modeloevaluativo[0],
                                                                                 inscrito=alumno,
                                                                                 cabeceranota__instructor__capeventoperiodo=instructor.capeventoperiodo,
                                                                                 cabeceranota__instructor=instructor).order_by('-id').first()
                                        notaanterior = detalle.nota
                                        detalle.nota = float(notasmooc[0])
                                    else:
                                        detalle = CapDetalleNotaIpec(cabeceranota=modeloevaluativo[0],
                                                                     inscrito=alumno,
                                                                     observacion="IMPORTACIÓN AUTOMÁTICA",
                                                                     nota=float(notasmooc[0]))
                                    detalle.save()
                                    log(u'Actualizo nota en tarea de capacitacion IPEC: %s nota anterior: %s nota actualizada: %s del modelo de evaluativo %s' % (
                                        detalle, str(notaanterior), str(detalle.nota), detalle.cabeceranota.modelo), request, "edit")
                                    alumno.nofinal = detalle.inscrito.nota_total_evento_porinstructor(instructor.capeventoperiodo.id, instructor.pk)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos. %s" %ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'alumnos':
                try:
                    if 'idi' in request.GET and 'ide' in request.GET:
                        data['title'] = u'Alumnos inscritos'
                        intructor = CapInstructorIpec.objects.get(pk=int(request.GET['idi']), capeventoperiodo_id=int(request.GET['ide']))
                        data['evento'] = intructor.capeventoperiodo
                        data['intructor'] = intructor
                        data['modelosencabesados'] = intructor.modelo_calificacion_abreviado(intructor.capeventoperiodo)
                        data['alumnos'] = intructor.capeventoperiodo.inscritos()
                        return render(request, "ins_cursosipec/alumnos.html", data)
                except Exception as ex:
                    pass


            elif action == 'extraernotasmoodle':
                try:
                    data['title'] = u'Importar calificaciones de moodle'
                    data['instructor'] = instructor = CapInstructorIpec.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "ins_cursosipec/extraernotasmoodle.html", data)
                except Exception as ex:
                    pass


            elif action == 'descargarnotas':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_inscritos_notas' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 1
                    intructor = CapInstructorIpec.objects.get(pk=int(request.GET['idi']))
                    eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['idp']))
                    totalinscritos = eventoperiodo.capinscritoipec_set.filter(status=True)
                    modelos = intructor.modelo_calificacion_abreviado(intructor.capeventoperiodo)

                    columns = [
                        (u"N.", 2000),
                        (u"CEDULA", 4000),
                        (u"NOMBRES", 10000)
                    ]
                    for m in modelos:
                        columns.append((u'%s' % m[1], 4000))
                    columns.append(('Nota Final', 4000))
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    for lista in totalinscritos:
                        row_num += 1
                        campo2 = lista.participante.identificacion()
                        campo3 = lista.participante.nombre_completo_inverso()
                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        col = 3
                        total = 0
                        for m in modelos:
                            nota = lista.mi_nota_individual(m[0], eventoperiodo.id)
                            if nota:
                                nota= nota.nota
                            else:nota=0
                            total += nota if nota else 0
                            ws.write(row_num, col, nota if nota else '', font_style2)
                            col += 1
                        ws.write(row_num, col, total, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'notasmoodle':
                try:
                    data['title'] = u'Notas de moodle'
                    search = None
                    data['instructor'] = intructor = CapInstructorIpec.objects.get(pk=int(encrypt(request.GET['idi'])),
                                                              capeventoperiodo_id=int(encrypt(request.GET['ide'])))
                    data['evento'] = intructor.capeventoperiodo
                    data['modelosencabesados'] = intructor.modelo_calificacion_abreviado(intructor.capeventoperiodo)
                    inscritos = intructor.capeventoperiodo.list_inscritos_sin_costo()


                    # if 's' in request.GET:
                    #     search = request.GET['s']
                    #     ss = search.split(' ')
                    #     inscritos = inscritos.filter(
                    #         Q(participante__nombres__icontains=search) |
                    #         Q(participante__apellido1__icontains=search) |
                    #         Q(participante__apellido2__icontains=search) |
                    #         Q(participante__cedula__icontains=search) |
                    #         Q(participante__pasaporte__icontains=search) |
                    #         Q(participante__usuario__username__icontains=search),
                    #         status=True).distinct()
                    #
                    # numerofilas = 30
                    # paging = MiPaginador(inscritos, numerofilas)
                    # p = 1
                    # try:
                    #     paginasesion = 1
                    #     if 'paginador' in request.session:
                    #         paginasesion = int(request.session['paginador'])
                    #     if 'page' in request.GET:
                    #         p = int(request.GET['page'])
                    #         if p == 1:
                    #             numerofilasguiente = numerofilas
                    #         else:
                    #             numerofilasguiente = numerofilas * (p - 1)
                    #     else:
                    #         p = paginasesion
                    #         if p == 1:
                    #             numerofilasguiente = numerofilas
                    #         else:
                    #             numerofilasguiente = numerofilas * (p - 1)
                    #     try:
                    #         page = paging.page(p)
                    #     except:
                    #         p = 1
                    #     page = paging.page(p)
                    # except:
                    #     page = paging.page(p)
                    # request.session['paginador'] = p
                    # data['paging'] = paging
                    # data['page'] = page
                    # data['numerofilasguiente'] = numerofilasguiente
                    # data['numeropagina'] = p
                    # data['rangospaging'] = paging.rangos_paginado(p)
                    data['inscritos'] = inscritos
                    return render(request, "ins_cursosipec/alumnos_moodle.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        else:
            try:
                data['title'] = u'Mis Cursos Asigandos'
                data['cursos'] = CapInstructorIpec.objects.filter(status=True, instructorprincipal=True, instructor=persona).order_by('-capeventoperiodo__fechainicio')
                data['instructor'] = persona
                return render(request, "ins_cursosipec/view.html", data)
            except Exception as ex:
                pass
