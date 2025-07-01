from calendar import weekday

from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime
from decorators import last_access
from posgrado.forms import RegistroRequisitosMaestriaForm, RegistroRequisitosMaestriaForm1
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template

from settings import SERVER_RESPONSE
from sga.funciones import generar_nombre, log, validarcedula
from django.contrib import messages
from inno.models import Aula, PantallaAula

from django.forms import model_to_dict

from sga.models import MESES_CHOICES, DIAS_CHOICES
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['url_'] = request.path
    data['currenttime'] = datetime.now()
    data['server_response'] = SERVER_RESPONSE

    if request.method == 'POST':
        pass
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'actualizarhorario':
                try:
                    if 'idp' in request.GET:
                        if int(encrypt(request.GET['idp'])) != 0:
                            data['idp'] = id = encrypt(request.GET['idp'])
                            pantalla = PantallaAula.objects.get(status=True, id=id)
                            aula_ids = pantalla.detallepantallaaula_set.values_list('aula__id', flat=True).filter(status=True)
                            aula = Aula.objects.filter(status=True, clasificacion=1, id__in=aula_ids).order_by('nombre')
                        else:
                            aula = Aula.objects.filter(status=True, clasificacion=1).order_by('nombre')
                    else:
                        aula = Aula.objects.filter(status=True, clasificacion=1).order_by('nombre')

                    nombremes = MESES_CHOICES[datetime.now().date().month - 1][1]
                    weekday = DIAS_CHOICES[datetime.now().date().isoweekday() - 1][1]
                    data['weekday'] = weekday + ', ' + str(datetime.now().date().day) + ' de ' + nombremes + ' de ' + str(datetime.now().date().year)

                    data['dia'] = datetime.now().date().isoweekday()
                    data['fecha'] = datetime.now().date()

                    aulaslab = Aula.objects.filter(status=True, clasificacion=1, bloque_id=8).order_by('nombre')

                    data['aulas'] = aula
                    template = get_template('adm_laboratorioscomputacion/modal/contenidoarmadillo.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result':False,'mensaje':'Error. Detalle: %s'%(ex.__str__())})
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Reservación de laboratorios'
                hoy = datetime.now().date()
                if 'idp' in request.GET:
                    data['idp'] = id = encrypt(request.GET['idp'])
                    pantalla = PantallaAula.objects.get(status=True, id=id)
                    aula_ids = pantalla.detallepantallaaula_set.values_list('aula__id', flat=True).filter(status=True)
                    aula = Aula.objects.filter(status=True, clasificacion=1, id__in=aula_ids).order_by('nombre')
                else:
                    aula = Aula.objects.filter(status=True, clasificacion=1).order_by('nombre')

                nombremes = MESES_CHOICES[datetime.now().date().month - 1][1]
                weekday = DIAS_CHOICES[datetime.now().date().isoweekday() - 1][1]
                data['weekday'] = weekday + ', ' + str(datetime.now().date().day) + ' de ' + nombremes + ' de ' + str(datetime.now().date().year)

                data['dia'] = datetime.now().date().isoweekday()
                data['fecha'] = datetime.now().date()

                aulaslab = Aula.objects.filter(status=True, clasificacion=1, bloque_id=8).order_by('nombre')

                data['aulas'] = aula
                return render(request, "adm_laboratorioscomputacion/armadilloexterno.html", data)
            except Exception as ex:
                messages.error(request,'Error: %s'% ex.__str__())
                return HttpResponseRedirect(request.path)