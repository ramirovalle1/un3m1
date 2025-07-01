import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.forms import model_to_dict
from decorators import last_access, secure_module
from django.template import Context
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime, timedelta

# from postulate.adm_bancohabilitado import loadpersondesiste
from sga.models import CoordinadorCarrera
from postulate.models import Partida, PersonaAplicarPartida, CalificacionDisertacion, ModeloEvaluativoDisertacion, \
    PartidaTribunal, CalificacionEntrevista, PersonaIdiomaPartida, PersonaFormacionAcademicoPartida, \
    PersonaExperienciaPartida, PersonaCapacitacionesPartida, PersonaPublicacionesPartida, NotificacionGanador
from postulate.postular import validar_campos
from sagest.models import Departamento,DistributivoPersona
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, ACTUALIZAR_FOTO_ALUMNOS
from sga.commonviews import adduserdata, obtener_reporte
from postulate.forms import ConvocatoriaForm, PartidaForm, ConvocatoriaTerminosForm, AceptarDesistirForm
from sga.funciones import logobjeto, MiPaginador, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
#from postulate.funciones import generar_reporte_excel_por_query

from xlwt import *
import xlwt

import xlsxwriter
import io


@login_required(redirect_field_name='ret', login_url='/loginpostulate')
@secure_module
@last_access
# @transaction.atomic()
def view(request):
    global ex
    data = {}
    perfilprincipal, persona, periodo = request.session['perfilprincipal'], request.session['persona'], request.session['periodo']
    data['hoy'] = hoy = datetime.now().date()
    data['currenttime'] = datetime.now()
    data['perfil'] = persona.mi_perfil()
    data['periodo'] = periodo
    data['url_'] = request.path
    mis_cordinaciones = persona.mis_coordinaciones().values_list('id', flat=True)
    mi_departamento = persona.mi_departamento()
    data['puede_ver_todos_bancos'] = puede_ver_todos_bancos = request.user.has_perm('postulate.puede_ver_todos_bancos')
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'habilitarrevision':
            try:
                if PersonaAplicarPartida.objects.values('id').filter(status=True, pk=request.POST['id']).exists():
                    persona = PersonaAplicarPartida.objects.get(status=True, pk=request.POST['id'])
                    persona.finsegundaetapa = False
                    persona.save(request)
                    logobjeto(u'{} :Se habilito la revision de la segunda etapa' .format(persona.__str__()), request, "EditHabilitar", None, persona)
                    return JsonResponse({'result': True, 'mensaje': 'Ganador declarado correctamente!'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': u'Error al guardar los datos'})


        # if action == 'desistir':
        #     with transaction.atomic():
        #         try:
        #             form = AceptarDesistirForm(request.POST, request.FILES)
        #             valid_ext = [".pdf"]
        #             if not form.is_valid():
        #                 raise NameError(f'{[{k:v[0]} for k, v in form.errors.items()]}')
        #             newfile = None
        #             if 'archivo' in request.FILES:
        #                 newfile = request.FILES['archivo']
        #                 ext = newfile._name[newfile._name.rfind("."):]
        #                 if not ext in valid_ext:
        #                     raise NameError("Solo archivos de tipo pdf")
        #                 if newfile.size > 30943040:
        #                     raise NameError('El archivo supera los 30Mb')
        #                 newfile._name = generar_nombre("evidencia", newfile._name)
        #             id = request.POST.get('id')
        #             personaaplicapartida = PersonaAplicarPartida.objects.get(status=True, id=int(id))
        #             desiste_ = loadpersondesiste(persona=personaaplicapartida.persona)
        #             perdesiste = None
        #             if 'desiste' in desiste_:
        #                 perdesiste = desiste_['desiste']
        #             else:
        #                 raise NameError(desiste_['mensaje'])
        #             if perdesiste:
        #                 desiste = perdesiste
        #                 desiste.fecha = form.cleaned_data['fecha']
        #                 desiste.observacion = form.cleaned_data['observacion']
        #                 if newfile: desiste.archivo = newfile
        #             else:
        #                 desiste = NotificacionGanador(
        #                     # persona = personaaplicapartida.persona,
        #                     personaaplicapartida = personaaplicapartida,
        #                     fecha = form.cleaned_data['fecha'],
        #                     observacion = form.cleaned_data['observacion'],
        #                     archivo=newfile
        #                 )
        #             desiste.save(request)
        #             logobjeto(f'Agrego registro de persona deiste: {desiste.__str__()}',request,'add',None,desiste)
        #             return HttpResponseRedirect(f'{request.path}')
        #         except Exception as ex:
        #             transaction.set_rollback(True)
        #             err_ = f"{ex.__str__()}({sys.exc_info()[-1].tb_lineno})"
        #             return JsonResponse({'result':True, 'mensaje':err_})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        adduserdata(request, data)
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'verdetallepostulante':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['resp_campos'] = validar_campos(request, persona, partida)
                    data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                    data['persona'] = postulante.persona
                    data['posidiomas'] = PersonaIdiomaPartida.objects.filter(status=True,
                                                                             personapartida=postulante).order_by('id')
                    data['postitulacion'] = PersonaFormacionAcademicoPartida.objects.filter(status=True,
                                                                                            personapartida=postulante).order_by(
                        'id')
                    data['posexperiencia'] = PersonaExperienciaPartida.objects.filter(status=True,
                                                                                      personapartida=postulante).order_by(
                        'id')
                    data['poscapacitacion'] = PersonaCapacitacionesPartida.objects.filter(status=True,
                                                                                          personapartida=postulante).order_by(
                        'id')
                    data['pospublicacion'] = PersonaPublicacionesPartida.objects.filter(status=True,
                                                                                        personapartida=postulante).order_by(
                        'id')
                    template = get_template("postulate/adm_revisionpostulacion/verdetallepostulante.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'evaluardisertacion':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['modeloevaluativo'] = modeloevaluativo = ModeloEvaluativoDisertacion.objects.filter(status=True, vigente=True,pk =partida.convocatoria.modeloevaluativo.id).first()
                    data['calificacion'] = calificacion = CalificacionDisertacion.objects.filter(postulacion=postulante, status=True).first()
                    template = get_template("postulate/adm_segundaetapa/calificardisertacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'evaluarentrevista':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['postulante'] = postulante = PersonaAplicarPartida.objects.get(pk=id)
                    data['partida'] = partida = Partida.objects.get(pk=postulante.partida.pk)
                    data['tribunal'] = tribunal = PartidaTribunal.objects.filter(status=True, partida=partida, tipo=2).order_by('cargos')
                    data['calificacion'] = calificacion = CalificacionEntrevista.objects.filter(postulacion=postulante, status=True).first()
                    template = get_template("postulate/adm_segundaetapa/calificarentrevista.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': str(ex)})

            if action == 'excel_postulantes__all_banco_habilitados':
                try:
                    anioact = datetime.now().year
                    aniolimite = anioact - 2
                    __author__ = 'Unemi'
                    ahora = datetime.now()
                    time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                    name_file = f'reporte_banco_elegible_{time_codigo}.xlsx'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet("Postulantes")

                    fuenteencabezado = workbook.add_format({
                        'align': 'center',
                        'bg_color': '#1C3247',
                        'font_color': 'white',
                        'border': 1,
                        'font_size': 24,
                        'bold': 1
                    })

                    fuentecabecera = workbook.add_format({
                        'align': 'center',
                        'bg_color': 'silver',
                        'border': 1,
                        'bold': 1
                    })

                    formatoceldacenter = workbook.add_format({
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'})

                    formatoceldafecha = workbook.add_format({
                        'num_format': 'dd/mm/yyyy',
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'
                    })


                    columnas = [
                        ('Convocatoria', 100),
                        ('Categoría', 50),
                        ('Partida', 100),
                        ('Carrera', 100),
                        ('Dedicación', 100),
                        ('Apellidos', 100),
                        ('Nombres', 100),
                        ('Titulo 3° nivel', 250),
                        ('Titulo 4° nivel', 250),
                        ('Identificación', 100),
                        ('Correo', 100),
                        ('Telf.', 100),
                        ('Telf. Conv.', 100),
                        ('Fecha', 100),
                        ('Nota Meritos', 100),
                        ('Nota Disertación', 100),
                        ('Nota Entrevista', 200),
                        ('Nota Final', 30),
                        ('Revisado Por', 50),
                        ('Fecha Revisión', 50),
                    ]

                    ws.merge_range(0, 0, 0, 18, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', fuenteencabezado)
                    ws.merge_range(1, 0, 1, 18, 'LISTADO DE POSTULANTES', fuenteencabezado)

                    row_num, numcolum = 3, 0
                    for col_name in columnas:
                        ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                        ws.set_column(row_num, numcolum, col_name[1])
                        numcolum += 1

                    row_num += 1
                    listadodistributivo = DistributivoPersona.objects.values_list('persona_id', flat=True).filter( estadopuesto__id=1, status=True)
                    # partidas = Partida.objects.values_list('id', flat=True).filter(status=True, convocatoria__ffin__year__range =[aniolimite, anioact], carrera__coordinacion__id__in=mis_cordinaciones).order_by('convocatoria__descripcion')
                    filtro = Q(status=True, convocatoria__ffin__year__range=[aniolimite, anioact])

                    if not puede_ver_todos_bancos:
                        filtro &= (Q(carrera__coordinacion__id__in=mis_cordinaciones) |
                                   Q(convocatoria__departamento=mi_departamento))
                    partidas = Partida.objects.values_list('id', flat=True).filter(filtro).order_by('convocatoria__descripcion')
                    listado = PersonaAplicarPartida.objects.filter(status=True,nota_final__gte=70,
                                                                   partida_id__in=partidas,
                                                                   esganador=False).exclude(persona_id__in=listadodistributivo).order_by('-nota_final_meritos')
                    for det in listado:
                        ws.write(row_num, 0, det.partida.convocatoria.descripcion, formatoceldacenter)
                        ws.write(row_num, 1, det.partida.convocatoria.tipocontrato.nombre if det.partida.convocatoria.tipocontrato else '', formatoceldacenter)
                        ws.write(row_num, 2, det.partida.titulo, formatoceldacenter)
                        ws.write(row_num, 3, det.partida.carrera.nombre if det.partida.carrera else '' , formatoceldacenter)
                        ws.write(row_num, 4, det.partida.get_dedicacion_display(), formatoceldacenter)
                        ws.write(row_num, 5, "{} {}".format(det.persona.apellido1, det.persona.apellido2), formatoceldacenter)
                        ws.write(row_num, 6, det.persona.nombres, formatoceldacenter)
                        tercernivel = det.persona.mis_titulaciones().filter(titulo__nivel__nivel=3).order_by('-fecha_creacion').first()
                        if tercernivel:
                            nombretitulo = tercernivel.titulo.__str__() if tercernivel else ''
                        ws.write(row_num, 7, "{}".format(nombretitulo), formatoceldacenter)
                        cuartonivel = det.persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[4, 5]).order_by('-fecha_creacion').first()
                        if cuartonivel:
                            nombretitulo = cuartonivel.titulo.__str__() if cuartonivel else ''
                        ws.write(row_num, 8, "{}".format(nombretitulo), formatoceldacenter)
                        ws.write(row_num, 9, det.persona.cedula, formatoceldacenter)
                        ws.write(row_num, 10, det.persona.email, formatoceldacenter)
                        ws.write(row_num, 11, det.persona.telefono, formatoceldacenter)
                        ws.write(row_num, 12, det.persona.telefono_conv, formatoceldacenter)
                        ws.write(row_num, 13, det.fecha_creacion, formatoceldafecha)
                        ws.write(row_num, 14, det.nota_final_meritos, formatoceldacenter)
                        ws.write(row_num, 15, det.get_nota_final_disertacion(), formatoceldacenter)
                        ws.write(row_num, 16, det.get_nota_final_entrevista(), formatoceldacenter)
                        ws.write(row_num, 17, det.nota_final, formatoceldacenter)
                        ws.write(row_num, 18, det.revisado_por.username if det.revisado_por else '', formatoceldacenter)
                        ws.write(row_num, 19, det.fecha_revision, formatoceldafecha)
                        row_num += 1
                    workbook.close()
                    output.seek(0)
                    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename="{name_file}"'
                    return response
                except Exception as ex:
                    pass


            # if action == 'desistir':
            #     try:
            #         hoy = datetime.now().date()
            #         dos_anos_atras = hoy - timedelta(days=365 * 2)
            #         id = request.GET.get('id')
            #         data['filtro'] = perapli = PersonaAplicarPartida.objects.get(status=True, id=int(encrypt(id)))
            #         desiste = loadpersondesiste(persona=perapli.persona)
            #         perdesiste = None
            #         if 'desiste' in desiste:
            #             perdesiste = desiste['desiste']
            #         else:
            #             raise NameError(desiste['mensaje'])
            #         form = AceptarDesistirForm()
            #         if perdesiste:
            #             form.initial = model_to_dict(perdesiste)
            #         data['form'] = form
            #         template = get_template('postulate/adm_postulate/modal/formmodelo.html')
            #         res_js = {"result": True,"data":template.render(data)}
            #     except Exception as ex:
            #         err_ = f"{ex.__str__()}({sys.exc_info()[-1].tb_lineno})"
            #         res_js = {"result": False,"mensaje":err_}
            #     return JsonResponse(res_js)

        else:
            try:
                data['title'] = u'Banco Elegible'
                anioact = datetime.now().year
                aniolimite = anioact - 2
                listadodistributivo = DistributivoPersona.objects.values_list('persona_id',flat=True).filter(estadopuesto__id=1, status=True).distinct()
                filtro = Q(status=True, nota_final__gte=70, esganador=False,
                           partida__convocatoria__ffin__year__range=[aniolimite, anioact])

                if not puede_ver_todos_bancos:
                    filtro &= (Q(partida__carrera__coordinacion__id__in=mis_cordinaciones) |
                               Q(partida__convocatoria__departamento=mi_departamento))

                eListaPersonaAplicarPartida = PersonaAplicarPartida.objects.filter(filtro).exclude(persona_id__in=listadodistributivo)
                search, url_vars = request.GET.get('s', ''), ''
                if search:
                    data['s'] = search = request.GET['s'].strip()
                    ss = search.split(' ')
                    url_vars += "&s={}".format(search)
                    if len(ss) == 1:
                        eListaPersonaAplicarPartida = eListaPersonaAplicarPartida.filter(Q(persona__nombres__icontains=search) |
                                         Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) |
                                         Q(persona__cedula=search)| Q(partida__codpartida__icontains=search)| Q(partida__convocatoria__descripcion__icontains=search))
                    else:
                        eListaPersonaAplicarPartida = eListaPersonaAplicarPartida.filter(
                            (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))
                             | Q(partida__codpartida__icontains=ss[0])
                             | Q(partida__codpartida__icontains=ss[1])
                             | Q(partida__convocatoria__descripcion__icontains=ss[0])
                             | Q(partida__convocatoria__descripcion__icontains=ss[1]))
                paging = MiPaginador(eListaPersonaAplicarPartida, 20)
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
                data['url_vars'] = url_vars
                data['listado'] = page.object_list
                return render(request, "postulate/adm_bancoelegible/view.html", data)
            except Exception as ex:
                pass