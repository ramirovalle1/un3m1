# -*- coding: latin-1 -*-
#decoradores

from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.forms import model_to_dict
from decorators import last_access, secure_module
from empleo.models import OfertaLaboralEmpresa, PersonaAplicaOferta
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime

from postulate.postular import validar_campos
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, email_valido, MiPaginador
from sga.models import miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginempleo')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['url_'] = request.path
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo

    if request.method == 'POST':
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'verdetalle':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['nopostula'] = nopostula = 'nopostula' in request.GET
                    data['estado'] = int(request.GET['estado'])
                    data['filtro'] = filtro = OfertaLaboralEmpresa.objects.get(pk=id)
                    data['resp_campos'] = validar_campos(request, persona, filtro)
                    template = get_template("empleo/postular/verdetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Mis Postulaciones'
                criterio, filtro, url_vars = request.GET.get('criterio', ''), (Q(status=True) & Q(persona=persona)), ''

                if criterio:
                    data['criterio'] = criterio
                    url_vars += "&criterio={}".format(criterio)
                    filtro = filtro & (Q(oferta__titulo__icontains=criterio)|Q(oferta__empresa__nombre__icontains=criterio) | Q(oferta__empresa__nombrecorto__icontains=criterio))

                listado = PersonaAplicaOferta.objects.filter(filtro).order_by('-id')
                data['vacio'] = 'No existen resultados para tu busqueda' if len(filtro) else 'No existen postulaciones realizadas'
                paging = MiPaginador(listado, 20)
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
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['list_count'] = len(listado)
                data['numpartidas'] = OfertaLaboralEmpresa.objects.values('id').filter(status=True, vigente=True, finicio__lte=hoy, ffin__gte=hoy).count()
                return render(request, "empleo/mispostulaciones/view.html", data)
            except Exception as ex:
                pass

