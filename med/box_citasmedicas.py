# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from med.forms import PersonaConsultaMedicaForm
from med.models import PersonaConsultaMedica, ProximaCita
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import Persona


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'consultamedica':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                f = PersonaConsultaMedicaForm(request.POST)
                if f.is_valid():
                    consulta = PersonaConsultaMedica(persona=persona,
                                                     fecha=datetime.now(),
                                                     pacientegrupo=f.cleaned_data['grupo'],
                                                     tipoatencion=f.cleaned_data['tipoatencion'],
                                                     motivo=f.cleaned_data['motivo'],
                                                     medicacion=f.cleaned_data['medicacion'],
                                                     diagnostico=f.cleaned_data['diagnostico'],
                                                     tratamiento=f.cleaned_data['tratamiento'],
                                                     medico=request.session['persona'])
                    consulta.save(request)
                    if f.cleaned_data['cita']:
                        if f.cleaned_data['fecha'] < datetime.now().date():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha de próxima cita incorrecta."})
                        proximacita = ProximaCita(persona=consulta.persona,
                                                  fecha=f.cleaned_data['fecha'],
                                                  hora=f.cleaned_data['hora'],
                                                  medico=consulta.medico,
                                                  indicaciones=f.cleaned_data['indicaciones'],
                                                  tipoconsulta=1)
                        proximacita.save(request)
                    log(u'Adiciono consulta medica: %s' % persona, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'noasistio':
            try:
                pc = ProximaCita.objects.get(pk=request.POST['id'])
                pc.asistio = True
                pc.save(request)
                log(u'Asistio a cita medica: %s [%s]' % (pc,pc.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:

        data['title'] = u'Citas medicas'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'consultamedica':
                try:
                    data['title'] = u'Consultas médicas'
                    data['persona'] = persona = Persona.objects.get(pk=request.GET['id'])
                    form = PersonaConsultaMedicaForm(initial={'fecha': datetime.now().date(),
                                                              'hora': "12:00"})
                    form.grupos_paciente(persona.grupos())
                    data['form'] = form
                    return render(request, "box_medical/consultamedica.html", data)
                except Exception as ex:
                    pass

            if action == 'noasistio':
                try:
                    data['title'] = u'No asistió a consulta'
                    data['pc'] = ProximaCita.objects.get(pk=request.GET['id'])
                    return render(request, "box_citasmedicas/noasistio.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            persona = data['persona']
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    proxima_cita = ProximaCita.objects.filter(Q(tipoconsulta__icontains=search) |
                                                              Q(persona__nombres__icontains=search) |
                                                              Q(persona__apellido1__icontains=search) |
                                                              Q(persona__apellido2__icontains=search) |
                                                              Q(persona__cedula__icontains=search), medico=persona).distinct()
                else:
                    proxima_cita = ProximaCita.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                              Q(persona__apellido2__icontains=ss[1]), medico=persona).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                proxima_cita = ProximaCita.objects.filter(id=ids, medico=persona)
            else:
                proxima_cita = ProximaCita.objects.filter(medico=persona)
            paging = MiPaginador(proxima_cita, 25)
            p = 1
            try:
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                page = paging.page(p)
            except Exception as ex:
                p = 1
                page = paging.page(p)
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['proxima_cita'] = page.object_list
            return render(request, "box_citasmedicas/view.html", data)