# -*- coding: latin-1 -*-
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import last_access
from med.forms import SubirDocumentoExamenLabForm
from med.models import PersonaExamenFisico, PatologicoPersonal, PatologicoQuirurgicos, AntecedenteTraumatologicos, \
    AntecedenteGinecoobstetrico, Habito, PersonaFichaMedica
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, variable_valor
from sga.models import Persona, miinstitucion, PersonaDatosFamiliares
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'subirdocumento':
            try:
                f = SubirDocumentoExamenLabForm(request.POST, request.FILES)
                newfile = None

                if not 'archivoexamenlaboratorio' in request.FILES:
                    return JsonResponse({"result": "bad", "mensaje": u"Atención, debe seleccionar un archivo en formato PDF."})

                if 'archivoexamenlaboratorio' in request.FILES:
                    arch = request.FILES['archivoexamenlaboratorio']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    fichamedica = PersonaFichaMedica.objects.get(personaextension__persona=persona)
                    newfile = request.FILES['archivoexamenlaboratorio']
                    newfile._name = generar_nombre("rexlab", newfile._name)
                    fichamedica.archivoexamenlaboratorio = newfile
                    fichamedica.estadorevisionexlab = 1
                    fichamedica.save(request)

                    log(u'Agregó archivo de resultado de exámenes de laboratorio: %s' % fichamedica, request, "edit")

                    # Médico área de bienestar estudiantil - envio de e-mail
                    medico = Persona.objects.get(pk=27961)
                    if medico:
                        tituloemail = "Registro de Resultado de exámenes de laboratorio - " + str(persona)

                        send_html_mail(tituloemail,
                                       "emails/notificacion_rexlab.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'fase': 'SUB',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'medico': medico,
                                        'estudiante': persona,
                                        'autoridad2': '',
                                        't': miinstitucion()
                                        },
                                       medico.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Solicitud Incorrecta."}), content_type="application/json")
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            pex = PersonaExamenFisico.objects.get(personafichamedica__personaextension__persona=persona)
            data['persona'] = persona

            if action == 'subirdocumento':
                try:
                    data['title'] = u'Subir documento de resultado de exámenes'
                    form = SubirDocumentoExamenLabForm()
                    data['form'] = form

                    return render(request, "alu_medical/subirdocumentoresultado.html", data)
                except Exception as ex:
                    pass

        else:
            #solo esta parte se llama
            data['title'] = u'Ficha médica'
            persona = request.session['persona']
            data['persona'] = persona
            data['hijo'] = PersonaDatosFamiliares.objects.db_manager("sga_select").filter(parentesco_id__in=[11, 14], persona=persona)
            data['pex'] = pex = persona.datos_examen_fisico()
            data['patologicofamiliar'] = pex.personafichamedica.patologicofamiliar_set.all()
            data['patologicopersonal'] = PatologicoPersonal.objects.get(personafichamedica=pex.personafichamedica) if PatologicoPersonal.objects.filter(personafichamedica=pex.personafichamedica).exists() else ''
            data['patologicoquirurgico'] = PatologicoQuirurgicos.objects.get(personafichamedica=pex.personafichamedica) if PatologicoQuirurgicos.objects.filter(personafichamedica=pex.personafichamedica).exists() else ''
            data['antecedentetraumatologico'] = AntecedenteTraumatologicos.objects.get(personafichamedica=pex.personafichamedica) if AntecedenteTraumatologicos.objects.filter(personafichamedica=pex.personafichamedica).exists() else ''
            data['antecedenteginecoobstetrico'] = AntecedenteGinecoobstetrico.objects.get(personafichamedica=pex.personafichamedica) if AntecedenteGinecoobstetrico.objects.filter(personafichamedica=pex.personafichamedica).exists() else ''
            data['hibito'] = Habito.objects.get(personafichamedica=pex.personafichamedica) if Habito.objects.filter(personafichamedica=pex.personafichamedica).exists() else ''
            return render(request, "alu_medical/datos.html", data)