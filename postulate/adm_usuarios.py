import random
#decoradores
import sys
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template.loader import get_template
from django.forms import model_to_dict
from decorators import last_access, secure_module

from django.template import Context
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime

from postulate.models import Convocatoria, Partida, ConvocatoriaTerminosCondiciones, PartidaAsignaturas
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, ACTUALIZAR_FOTO_ALUMNOS
from sga.commonviews import adduserdata, obtener_reporte
from postulate.forms import ConvocatoriaForm, PartidaForm, ConvocatoriaTerminosForm
from sga.funciones import log, MiPaginador, resetear_clave, resetear_clave_postulate,logobjeto

from sga.models import AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, Carrera, Asignatura, Titulo, Postulante, Persona, miinstitucion, CUENTAS_CORREOS, Group
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt



@login_required(redirect_field_name='ret', login_url='/loginpostulate')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    periodo = request.session['periodo']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo
    idgrupo = 420
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'changepass':
            try:
                with transaction.atomic():
                    persona_ = Persona.objects.get(id=int(request.POST['id']))
                    password, anio = '', ''
                    if persona_.nacimiento:
                        anio = "*" + str(persona_.nacimiento)[0:4]
                    password = persona_.cedula.strip() + anio
                    resetear_clave_postulate(persona_)
                    send_html_mail("CONTRASEÑA RESTAURADA", "emails/postulate_cambiar_pass.html",
                                   {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': persona_, 'pass': password,
                                    't': miinstitucion()}, [persona_.email], [], cuenta=CUENTAS_CORREOS[30][1])
                    emailpersona = "{}*****@{}".format(persona_.email.split('@')[0][:3], persona_.email.split('@')[1])
                    msg = "Se restablecio contraseña {}, verificar su nueva contraseña en el correo {}".format(password, emailpersona)
                    log(u'Cambio Contraseña: %s' % persona_, request, "changepasspostulate")
                    res_json = {"error": False, "message": msg}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'habilitarbancospostulate':
            try:
                postulante = Postulante.objects.get(persona_id=request.POST['id'])
                grupo = Group.objects.get(id=idgrupo)
                grupo.user_set.add(postulante.persona.usuario)
                grupo.save()
                logobjeto(u'Adiciono grupo de usuarios: %s' % postulante, request, "add", None, postulante)
                return JsonResponse({"result": 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                lineaerror = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {} {}".format(str(ex), lineaerror)})

        if action == 'deshabilitarbancospostulate':
            try:
                postulante = Postulante.objects.get(persona_id=request.POST['id'])
                grupo = Group.objects.get(id=idgrupo)
                grupo.user_set.remove(postulante.persona.usuario)
                grupo.save()
                logobjeto(u'Elimino de grupo de usuarios: %s' % postulante, request, "del", None, postulante)
                return JsonResponse({"result": 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                lineaerror = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {} {}".format(str(ex), lineaerror)})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # fin get
        adduserdata(request, data)
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

        else:
            try:
                data['title'] = u'Usuarios'
                search, filtro, url_vars = request.GET.get('s', ''), (Q(status=True) & Q(activo=True)), ''

                if search:
                    data['search'] = search
                    url_vars += "&s={}".format(search)
                    s = search.split()
                    if len(s) == 1:
                        filtro = filtro & (Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__apellido1__icontains=search))
                    else:
                        filtro = filtro & (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]))
                listado = Postulante.objects.filter(filtro).order_by('-id')
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
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                data['page'] = page
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['list_count'] = len(listado)
                return render(request, "postulate/adm_usuarios/view.html", data)
            except Exception as ex:
                pass