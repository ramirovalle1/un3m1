# -*- coding: UTF-8 -*-
import random
from datetime import date
from xlwt import *

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from sagest.models import DistributivoPersona, ModalidadLaboral, RegimenLaboral
from settings import ALUMNOS_GROUP_ID

from sga.commonviews import adduserdata

from sga.models import Periodo, Persona


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'exportarpublime':
            try:
                datos = request.POST['datos']
                msj = request.POST['msj']
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('texto')
                response = HttpResponse(content_type="application/ms-excel")
                response[
                    'Content-Disposition'] = 'attachment; filename=personal_publimes' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"Numero", 4000),
                    (u"Texto", 7000)
                ]
                row_num =0
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 1
                if 'idper' in request.POST and 'lista' in request.POST:
                    idper = request.POST['idper']
                    lista = request.POST['lista']
                    persona = Persona.objects.filter(inscripcion__matricula__nivel__periodo__id__in=[int(x) for x in idper.split(',')],
                                                    id__in=[int(x) for x in datos.split(',')],
                                                    usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
                    for p in persona:
                        if p.telefono and p.telefono.__len__()==10 and  p.telefono.isdigit():
                            campo1 = p.telefono
                            campo2 = msj
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            row_num += 1
                    distributivo = DistributivoPersona.objects.filter(id__in=[int(x) for x in datos.split(',')],
                                                                      regimenlaboral__id__in=[int(x) for x in lista.split(',')],
                                                                      estadopuesto_id=1, status=True,
                                                                      regimenlaboral__status=True,
                                                                      nivelocupacional__status=True,
                                                                      modalidadlaboral__status=True,
                                                                      denominacionpuesto__status=True,
                                                                      unidadorganica__status=True,
                                                                      persona__status=True)
                    for x in distributivo:
                        if x.persona.telefono and x.persona.telefono.__len__() == 10 and x.persona.telefono.isdigit():
                            campo1 = x.persona.telefono
                            campo2 = msj
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            row_num += 1
                elif 'idper' in request.POST:
                    idper = request.POST['idper']
                    persona = Persona.objects.filter(inscripcion__matricula__nivel__periodo__id__in=[int(x) for x in idper.split(',')],
                        id__in=[int(x) for x in datos.split(',')],
                        usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
                    for p in persona:
                        if p.telefono and p.telefono.__len__() == 10 and p.telefono.isdigit():
                            campo1 = p.telefono
                            campo2 = msj
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            row_num += 1
                elif 'lista' in request.POST:
                    lista = request.POST['lista']
                    distributivo = DistributivoPersona.objects.filter(id__in=[int(x) for x in datos.split(',')],
                                                                      regimenlaboral__id__in=[int(x) for x in lista.split(',')],
                                                                      estadopuesto_id=1, status=True,
                                                                      regimenlaboral__status=True,
                                                                      nivelocupacional__status=True,
                                                                      modalidadlaboral__status=True,
                                                                      denominacionpuesto__status=True,
                                                                      unidadorganica__status=True,
                                                                      persona__status=True)
                    for x in distributivo:
                        if x.persona.telefono and x.persona.telefono.__len__() == 10 and x.persona.telefono.isdigit():
                            campo1 = x.persona.telefono
                            campo2 = msj
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            row_num += 1

                wb.save(response)
                return response
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'PUBLIMES'
            idper = None
            lista = None
            msj = None
            if 'msj' in request.GET:
                msj = request.GET['msj']
            if 'idper' in request.GET and 'lista' in request.GET :
                idper = request.GET['idper']
                lista = request.GET['lista']
                data['distributivo']=DistributivoPersona.objects.filter(regimenlaboral__id__in=[int(x) for x in lista.split(',')], estadopuesto_id=1,status=True,
                                                                        regimenlaboral__status=True,
                                                                        nivelocupacional__status=True,
                                                                        modalidadlaboral__status=True,
                                                                        denominacionpuesto__status=True,
                                                                        unidadorganica__status=True,
                                                                        persona__status=True).order_by('persona__apellido1','persona__apellido2')
                data['persona'] = Persona.objects.filter(inscripcion__matricula__nivel__periodo__id__in=[int(x) for x in idper.split(',')],
                                                         usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            elif 'idper' in request.GET:
                idper = request.GET['idper']
                data['distributivo'] = Persona.objects.filter(inscripcion__matricula__nivel__periodo__id__in=[int(x) for x in idper.split(',')],
                                                              usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            elif 'lista' in request.GET:
                lista = request.GET['lista']
                data['distributivo'] =  DistributivoPersona.objects.filter(regimenlaboral__id__in=[int(x) for x in lista.split(',')], estadopuesto_id=1,
                                                                           status=True,
                                                                           regimenlaboral__status=True,
                                                                           nivelocupacional__status=True,
                                                                           modalidadlaboral__status=True,
                                                                           denominacionpuesto__status=True,
                                                                           unidadorganica__status=True,
                                                                           persona__status=True).order_by('persona__apellido1', 'persona__apellido2')
            data['idper'] = idper if idper else ""
            data['lista'] = lista if lista else ""
            data['msj'] = msj if msj else ""
            x=[5,3]
            data['regimen'] = RegimenLaboral.objects.filter(status=True).exclude(id__in=x)
            data['modalidad'] = ModalidadLaboral.objects.filter(status=True)
            hoy = date.today()
            data['periodo'] = Periodo.objects.filter(status=True,activo=True,visible=True,inicio__lte=hoy,fin__gte=hoy)
            return render(request, "publimes/view.html", data)