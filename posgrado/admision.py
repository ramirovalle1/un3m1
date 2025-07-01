# -*- coding: latin-1 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime
from decorators import last_access
from posgrado.forms import RegistroRequisitosMaestriaForm, RegistroRequisitosMaestriaForm1
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from sga.funciones import generar_nombre, log, validarcedula
from django.contrib import messages
from inno.models import ProgramaPac
from sga.models import Persona, Carrera, CUENTAS_CORREOS, CompendioSilaboSemanal, VideoMagistralSilaboSemanal, \
    Materia, RecursoTemaProgramaAnalitico, VideoTemaProgramaAnalitico, VideoSubTemaProgramaAnalitico, \
    DetalleSilaboSemanalTema, TipoDescuentoMatricula, DetalleConfiguracionDescuentoPosgrado, ItinerarioMallaEspecilidad,\
    Titulacion, CamposTitulosPostulacion, Titulo,AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, Graduado
from posgrado.models import PreInscripcion, FormatoCarreraIpec, EvidenciasMaestrias, CohorteMaestria, MaestriasAdmision, CONTACTO_MAESTRIA, \
    InscripcionCohorte, InscripcionAspirante, CanalInformacionMaestria
from posgrado.forms import TitulacionPersonaAdmisionPosgradoForm, RegistroAdmisionIpecForm
from django.forms import model_to_dict
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['url_'] = request.path
    data['currenttime'] = datetime.now()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'cargarcombo_titulacion':
                try:
                    persona = Persona.objects.filter(pk=request.POST['id']).last()
                    lista = []
                    if persona:
                        for titulo in persona.titulacion_set.filter(status=True, educacionsuperior=True):
                            lista.append([titulo.id, titulo.titulo.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'cargar_campostitulo':
                try:
                    t = None
                    if request.POST['id']:
                        t = Titulo.objects.filter(pk=request.POST['id']).first()
                    lista1 = []
                    if t:
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=t).first()
                        if campotitulo:
                            for ca in campotitulo.campoamplio.all():
                                lista1.append([ca.id, ca.__str__()])
                        else:
                            for ca in AreaConocimientoTitulacion.objects.filter(status=True, tipo=1).order_by('codigo'):
                                lista1.append([ca.id, ca.__str__()])
                    else:
                        for ca in AreaConocimientoTitulacion.objects.filter(status=True, tipo=1).order_by('codigo'):
                            lista1.append([ca.id, ca.__str__()])
                    return JsonResponse({'result': 'ok', 'lista1': lista1})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            elif action == 'cargar_todos':
                try:
                    t = Titulo.objects.filter(pk=request.POST['idtitulo']).first()
                    listaca = []
                    listace = []
                    listacd = []
                    campotitulo, campoamplio, campoespecifico, campodetallado = None, None, None, None
                    if CamposTitulosPostulacion.objects.filter(status=True, titulo=t).exists():
                        campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=t).first()
                        campoamplio = AreaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campoamplio.all().values_list('id', flat=True))
                        if campoamplio:
                            for ca in campoamplio:
                                listaca.append([ca.id, ca.__str__()])
                        campoespecifico = SubAreaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campoespecifico.all().values_list('id', flat=True))
                        if campoespecifico:
                            for ce in campoespecifico:
                                listace.append([ce.id, ce.__str__()])
                        campodetallado = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campodetallado.all().values_list('id', flat=True))
                        if campodetallado:
                            for cd in campodetallado:
                                listacd.append([cd.id, cd.__str__()])
                        return JsonResponse({"result": "ok", "campoamplio": listaca, "campoespecifico": listace,
                                             "campodetallado": listacd})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Seleccione título: mínimo de tercer nivel o superior."})

            if action == 'extraercampos':
                try:
                    titulacion = None
                    ce = 'Campo Específico: '
                    if request.POST['id']:
                        titulacion = Titulacion.objects.filter(pk=request.POST['id']).last()
                    if titulacion:
                        campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo)
                        for campotitulo in campotitulos:
                            for campoe in campotitulo.campoespecifico.all():
                                ce = ce + campoe.__str__() + ' | '
                    return JsonResponse({'result': 'ok', 'ce': ce})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            if action == 'addpersona':
                try:
                    f = RegistroAdmisionIpecForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['cedula'][:2] == u'VS' or f.cleaned_data['cedula'][:2] == u'vs':
                            # if not Persona.objects.filter(pasaporte=f.cleaned_data['cedula'][2:]).exists():
                            if not Persona.objects.filter(pasaporte=f.cleaned_data['cedula']).exists():
                                persona = Persona(pasaporte=f.cleaned_data['cedula'],
                                                  nombres=f.cleaned_data['nombres'],
                                                  apellido1=f.cleaned_data['apellido1'],
                                                  apellido2=f.cleaned_data['apellido2'],
                                                  email=f.cleaned_data['email'],
                                                  telefono=f.cleaned_data['telefono'],
                                                  sexo_id=request.POST['genero'],
                                                  nacimiento='1999-01-01',
                                                  pais_id=request.POST['pais'],
                                                  provincia_id=request.POST['provincia'],
                                                  canton_id=request.POST['canton'],
                                                  direccion=request.POST['direccion'],
                                                  direccion2=''
                                                  )
                                persona.save(request)
                                # log(u'Adiciono persona formulario externo de admision posgrado: %s' % persona, request, "add")
                            else:
                                persona = Persona.objects.filter(pasaporte=f.cleaned_data['cedula']).last()
                                persona.email = f.cleaned_data['email']
                                persona.telefono = f.cleaned_data['telefono']
                                persona.pais_id = request.POST['pais']
                                persona.provincia_id = request.POST['provincia']
                                persona.canton_id = request.POST['canton']
                                persona.direccion = request.POST['direccion']
                                persona.save(request)
                                # log(u'Editó persona: %s' % persona, request, "edit")
                        else:
                            if not Persona.objects.filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula']),status=True).exists():
                                persona = Persona(cedula=f.cleaned_data['cedula'],
                                                  nombres=f.cleaned_data['nombres'],
                                                  apellido1=f.cleaned_data['apellido1'],
                                                  apellido2=f.cleaned_data['apellido2'],
                                                  email=f.cleaned_data['email'],
                                                  telefono=f.cleaned_data['telefono'],
                                                  sexo_id=request.POST['genero'],
                                                  nacimiento='1999-01-01',
                                                  pais_id=request.POST['pais'],
                                                  provincia_id=request.POST['provincia'],
                                                  canton_id=request.POST['canton'],
                                                  direccion=request.POST['direccion'],
                                                  direccion2=''
                                                  )
                                persona.save(request)
                                # log(u'Adiciono persona formulario externo de admision posgrado: %s' % persona, request, "add")
                            else:
                                persona = Persona.objects.filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula'])).first()
                                persona.email = f.cleaned_data['email']
                                persona.telefono = f.cleaned_data['telefono']
                                persona.pais_id = request.POST['pais']
                                persona.provincia_id = request.POST['provincia']
                                persona.canton_id = request.POST['canton']
                                persona.direccion = request.POST['direccion']
                                persona.save(request)
                                # log(u'Editó persona formulario externo de admision posgrado: %s' % persona, request, "edit")
                        return JsonResponse({'result': 'ok',"idpersona": persona.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            if action == 'addregistro':
                try:
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip()
                    tipoiden = request.POST['id_tipoiden']
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    carrera = request.POST['carrera']
                    email = request.POST['email']
                    telefono = request.POST['telefono']
                    datospersona=None
                    formato = FormatoCarreraIpec.objects.filter(carrera=carrera, status=True)[0]
                    if tipoiden == '1':
                        if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                            datospersona = Persona.objects.get(Q(cedula=cedula) | Q(pasaporte=cedula))
                            datospersona.email = email
                            datospersona.telefono = telefono
                            datospersona.save(request)
                        else:
                            datospersona = Persona(cedula=cedula,
                                                   nombres=nombres,
                                                   apellido1=apellido1,
                                                   apellido2=apellido2,
                                                   email=email,
                                                   telefono=telefono,
                                                   nacimiento=datetime.now().date()
                                                   )
                            datospersona.save(request)

                    if tipoiden == '2':
                        if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                            datospersona = Persona.objects.get(Q(cedula=cedula) | Q(pasaporte=cedula))
                            datospersona.email = email
                            datospersona.telefono = telefono
                            datospersona.save(request)
                        else:
                            datospersona = Persona(pasaporte=cedula,
                                                   nombres=nombres,
                                                   apellido1=apellido1,
                                                   apellido2=apellido2,
                                                   email=email,
                                                   telefono=telefono,
                                                   nacimiento=datetime.now().date()
                                                   )
                            datospersona.save(request)

                    if datospersona:
                        if datospersona.preinscripcion_set.filter(carrera_id=carrera, status=True).exists():
                            return JsonResponse({'result': 'bad', "mensaje": u"Usted ya se encuentra inscrito."})
                        else:
                            preinscrito = PreInscripcion(persona=datospersona,
                                                         fecha_hora=hoy,
                                                         carrera_id=carrera,
                                                         formato= formato
                                                         )

                            preinscrito.save(request)

                        lista = []
                        if preinscrito.persona.emailinst:
                            lista.append(preinscrito.persona.emailinst)
                        if preinscrito.persona.email:
                            lista.append(preinscrito.persona.email)
                        if formato.correomaestria:
                            lista.append(formato.correomaestria)
                        lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
                        asunto = u"Confirmación de pre-inscripción de maestría"
                        send_html_mail(asunto, "emails/notificacion_preinscripcion_ipec.html",
                                            {'sistema': 'Posgrado UNEMI', 'preinscrito': preinscrito,'formato': formato.banner},
                                            lista, [], [],
                                            cuenta=CUENTAS_CORREOS[18][1])

                    # if carrera == '60':
                    #     lista = []
                    #     lista.append('maestria.economia-desarrolloproductivo@unemi.edu.ec')
                    #     asunto = u"Nueva inscripción a la carrera"
                    #     send_html_mail(asunto, "emails/notificacion_nueva_preinscripcion_ipec.html",
                    #                    {'sistema': 'Posgrado', 'preinscrito': preinscrito},
                    #                    lista, [], [],
                    #                    cuenta=CUENTAS_CORREOS[18][1])

                    #else:

                        return JsonResponse({'result': 'ok', "mensaje": u"Sus datos se enviaron correctamente, por favor revisar la notificación enviada a su correo."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            elif action == 'consultacedula':
                try:
                    cedula = request.POST['cedula'].strip()
                    hoy = datetime.now().date()
                    if request.POST['tipoidentificacion'].strip() == '1':
                        resp = validarcedula(cedula)
                        if resp != 'Ok':
                            raise NameError(u"%s."%(resp))

                    itinerario = 0
                    if 'itinerario' in request.POST:
                        if request.POST['itinerario'] != '':
                            itinerario = request.POST['itinerario']

                    nomcarrera = Carrera.objects.filter(pk=request.POST['carrera'])[0]
                    datospersona = None
                    provinciaid = 0
                    cantonid = 0
                    cantonnom = ''
                    lugarestudio = ''
                    carrera = ''
                    profesion = ''
                    institucionlabora = ''
                    cargo = ''
                    teleoficina = ''
                    idgenero = 0
                    habilitaemail = 0
                    if cedula:
                        if Persona.objects.filter(cedula=cedula).exists():
                            datospersona = Persona.objects.get(cedula=cedula)
                        elif Persona.objects.filter(pasaporte=cedula).exists():
                            datospersona = Persona.objects.get(pasaporte=cedula)
                    if datospersona:

                        postulante = datospersona
                        # valida ya está graduado en la maestria
                        if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                            if Graduado.objects.filter(status=True, inscripcion__persona=postulante, inscripcion__carrera=nomcarrera, inscripcion__itinerario=itinerario).exists():
                                raise NameError(u"Usted ya se encuentra graduado en la maestría y mención seleccionada")

                            if InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante, cohortes__maestriaadmision__carrera=nomcarrera, activo=True, status=True, itinerario=itinerario).exists():
                                obtenerinscripcion = InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                                                                  cohortes__maestriaadmision__carrera=nomcarrera,
                                                                  activo=True, status=True, itinerario=itinerario)[0]
                                raise NameError(u"Usted ya se encuentra registrado, en la cohorte %s. Un asesor/a lo contactará en el menor tiempo posible, revise su correo electrónico para más información." % (obtenerinscripcion.cohortes))
                        else:
                            if Graduado.objects.filter(status=True, inscripcion__persona=postulante, inscripcion__carrera=nomcarrera).exists():
                                raise NameError("Usted ya se encuentra graduado en la maestría seleccionada")

                            if InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante, cohortes__maestriaadmision__carrera=nomcarrera, activo=True, status=True).exists():
                                obtenerinscripcion = InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                                                                  cohortes__maestriaadmision__carrera=nomcarrera,
                                                                  activo=True, status=True)[0]
                                raise NameError(u"Usted ya se encuentra registrado, en la cohorte %s. Un asesor/a lo contactará en el menor tiempo posible, revise su correo electrónico para más información." % (obtenerinscripcion.cohortes))

                        obtenerinscripcion = None
                        # valida ya está registrado en la maestria
                        # valida si no esta registrado en otras maestrias
                        inscripcionesenotracohortes = InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                                                                                        activo=True,
                                                                                        status=True).exclude(
                            cohortes__maestriaadmision__carrera=nomcarrera)
                        if inscripcionesenotracohortes.values('id').exists():
                            for otracohorte in inscripcionesenotracohortes:
                                re = (hoy - otracohorte.fecha_creacion.date()).days
                                if otracohorte.matricula_activa_cohorte() == False:
                                    if otracohorte.doblepostulacion == False:
                                        if re > 365:
                                            otracohorte.status = False
                                            otracohorte.save()
                                # if not graduado.values('id').filter(inscripcion__carrera=otracohorte.cohortes.maestriaadmision.carrera).exists():
                                #     raise NameError(u"Usted ya esta registrado en la maestría %s" % (otracohorte.cohortes.maestriaadmision.carrera))
                        return JsonResponse({"result": "ok", "idpersona": datospersona.id, "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                             "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "genero":datospersona.sexo.id,
                                             "pais": datospersona.pais.id if datospersona.pais else 0,"provincia": datospersona.provincia.id if datospersona.provincia else 0, "canton": datospersona.canton.id if datospersona.canton else 0, "direccion": datospersona.direccion})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

            elif action == 'addtitulacionpos':
                try:
                    with transaction.atomic():
                        persona = Persona.objects.get(pk=int(request.POST['idpersona']))
                        f = TitulacionPersonaAdmisionPosgradoForm(request.POST, request.FILES)
                        if 'registroarchivo' in request.FILES:
                            registroarchivo = request.FILES['registroarchivo']
                            extencion1 = registroarchivo._name.split('.')
                            exte1 = extencion1[1]
                            if registroarchivo.size > 4194304:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                            if not exte1 == 'pdf' and not exte1 == 'png' and not exte1 == 'jpg' and not exte1 == 'jpeg' and not exte1 == 'jpg':
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Archivo SENESCYT solo en formato .pdf, jpg, jpeg, png"})
                        if f.is_valid():
                            if persona:
                                titulo = None
                                if request.POST['registrartitulo'] == 'true':

                                    if Titulo.objects.filter(nombre__unaccent=f.cleaned_data['nombre'].upper()).exists():
                                        return JsonResponse({"result": "bad", "mensaje": u"Imposible guardar registro. El títullo %s ya se encuentra registrado." %(f.cleaned_data['nombre'])})
                                    if Titulo.objects.filter(nombre=f.cleaned_data['nombre'].upper(), nivel=f.cleaned_data['nivel']).exists():
                                        return JsonResponse({"result": "bad", "mensaje": u"Imposible guardar registro. El título %s ya se encuentra registrado." %(f.cleaned_data['nombre'])})
                                    if f.cleaned_data['nivel'].id == 4 and not f.cleaned_data['grado']:
                                        return JsonResponse({"result": "bad", "mensaje": u"Por favor seleccione grado."})

                                    titulo = Titulo(nombre=f.cleaned_data['nombre'],
                                                    abreviatura=f.cleaned_data['abreviatura'],
                                                    nivel=f.cleaned_data['nivel'],
                                                    grado=f.cleaned_data['grado'],
                                                    areaconocimiento= f.cleaned_data['campoamplio'][0],
                                                    subareaconocimiento = f.cleaned_data['campoespecifico'][0],
                                                    subareaespecificaconocimiento=f.cleaned_data['campodetallado'][0]
                                                    )
                                    titulo.save(request)
                                    titulacion = Titulacion(persona=persona,
                                                            titulo=titulo,
                                                            registro=f.cleaned_data['registro'],
                                                            pais=f.cleaned_data['pais'],
                                                            provincia=f.cleaned_data['provincia'],
                                                            canton=f.cleaned_data['canton'],
                                                            parroquia=f.cleaned_data['parroquia'],
                                                            educacionsuperior=True,
                                                            institucion=f.cleaned_data['institucion'])
                                    titulacion.save(request)
                                else:
                                    titulo = f.cleaned_data['titulo']
                                    if Titulacion.objects.filter(persona=persona,titulo=titulo).exists():
                                        raise NameError("No se puede guardar título. Usted ya tiene registrado su título %s."%(titulo))
                                    titulacion = Titulacion(persona=persona,
                                                            titulo=f.cleaned_data['titulo'],
                                                            registro=f.cleaned_data['registro'],
                                                            pais=f.cleaned_data['pais'],
                                                            provincia=f.cleaned_data['provincia'],
                                                            canton=f.cleaned_data['canton'],
                                                            parroquia=f.cleaned_data['parroquia'],
                                                            educacionsuperior=True,
                                                            institucion=f.cleaned_data['institucion'])
                                    titulacion.save(request)
                            if 'registroarchivo' in request.FILES:
                                newfile2 = request.FILES['registroarchivo']
                                if newfile2:
                                    newfile2._name = generar_nombre("archivosenecyt_", newfile2._name)
                                    titulacion.registroarchivo = newfile2
                                    titulacion.save(request)
                            campotitulo = None
                            if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).exists():
                                campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).first()
                            else:
                                campotitulo = CamposTitulosPostulacion(titulo=titulo)
                                campotitulo.save(request)

                            if not f.cleaned_data['campoamplio']:
                                if titulo.areaconocimiento:
                                    if not campotitulo.campoamplio.filter(id=titulo.areaconocimiento.id):
                                        campotitulo.campoamplio.add(titulo.areaconocimiento)
                                else:
                                    raise NameError("El título %s no cuenta con campo amplio, específico y detallado. Favor comuníquese con servicios informáticos (servicios.informaticos@unemi.edu.ec) para actualizar los datos del título." % (titulo))
                                if titulo.subareaconocimiento:
                                    if not campotitulo.campoespecifico.filter(id=titulo.subareaconocimiento.id):
                                        campotitulo.campoespecifico.add(titulo.subareaconocimiento)
                                if titulo.subareaespecificaconocimiento:
                                    if not campotitulo.campodetallado.filter(id=titulo.subareaespecificaconocimiento.id):
                                        campotitulo.campodetallado.add(titulo.subareaespecificaconocimiento)
                            else:
                                for ca in f.cleaned_data['campoamplio']:
                                    if not campotitulo.campoamplio.filter(id=ca.id):
                                        campotitulo.campoamplio.add(ca)
                                for ce in f.cleaned_data['campoespecifico']:
                                    if not campotitulo.campoespecifico.filter(id=ce.id):
                                        campotitulo.campoespecifico.add(ce)
                                for cd in f.cleaned_data['campodetallado']:
                                    if not campotitulo.campodetallado.filter(id=cd.id):
                                        campotitulo.campodetallado.add(cd)
                            campotitulo.save(request)
                            # log(u'Adiciono titulacion formulario externo de posgrado: %s' % titulacion, request, "add")
                            return JsonResponse({"result": "ok", "idpersona":persona.id})
                        else:
                            # raise NameError('Error')
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

            elif action == 'subirdocumentos':
                try:
                    if 'hojavida' in request.FILES != '' and 'copiavotacion' in request.FILES != '' and 'copiacedula' in request.FILES != '' and 'senescyt' in request.FILES != '':
                        inscripcion = PreInscripcion.objects.get(id=encrypt(request.POST['id']))
                        inscripcion.evidencias = True
                        inscripcion.save()
                        evidencia = EvidenciasMaestrias(preinscripcion=inscripcion)
                        evidencia.save()
                    newfile = None
                    if 'hojavida' in request.FILES != '':
                        newfilehojavida = request.FILES['hojavida']
                        if newfilehojavida:
                            newfilesd = newfilehojavida._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilehojavida.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilehojavida:
                                newfilehojavida._name = generar_nombre("requisitoipecpreinscrito", newfilehojavida._name)
                            evidencia.hojavida=newfilehojavida
                            evidencia.save()
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Falta hoja de vida."})

                    if 'copiavotacion' in request.FILES != '':
                        newfilecopiavotacion = request.FILES['copiavotacion']
                        if newfilecopiavotacion:
                            newfilesd = newfilecopiavotacion._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilecopiavotacion.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilecopiavotacion:
                                newfilecopiavotacion._name = generar_nombre("requisitoipecpreinscrito", newfilecopiavotacion._name)
                            evidencia.copiavotacion = newfilecopiavotacion
                            evidencia.save()
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta copia de votación."})

                    if 'copiacedula' in request.FILES != '':
                        newfilecopiacedula = request.FILES['copiacedula']
                        if newfilecopiacedula:
                            newfilesd = newfilecopiacedula._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilecopiacedula.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilecopiacedula:
                                newfilecopiacedula._name = generar_nombre("requisitoipecpreinscrito", newfilecopiacedula._name)
                            evidencia.copiacedula = newfilecopiacedula
                            evidencia.save()
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta copia de cédula."})

                    if 'senescyt' in request.FILES != '':
                        newfilesenescyt= request.FILES['senescyt']
                        if newfilesenescyt:
                            newfilesd = newfilesenescyt._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilesenescyt.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilesenescyt:
                                newfilesenescyt._name = generar_nombre("requisitoipecpreinscrito", newfilesenescyt._name)
                            evidencia.senescyt = newfilesenescyt
                            evidencia.save()
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta certificado de senescyt."})

                    if 'lenguaextranjera' in request.FILES:
                        newfilelenguaextranjera= request.FILES['lenguaextranjera']
                        if newfilelenguaextranjera:
                            newfilesd = newfilelenguaextranjera._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.doc', '.pdf', '.docx']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .doc y .pdf"})
                            if newfilelenguaextranjera.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            if newfilelenguaextranjera:
                                newfilelenguaextranjera._name = generar_nombre("requisitoipecpreinscrito", newfilelenguaextranjera._name)
                            evidencia.lenguaextranjera = newfilelenguaextranjera
                            evidencia.save()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, falta uno o varios documentos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'listcampoespecifico':
                try:
                    campoamplio = request.GET.get('campoamplio')
                    listcampoamplio = campoamplio
                    if len(campoamplio) > 1:
                        listcampoamplio = campoamplio.split(',')
                    querybase = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoamplio).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "idca": x.areaconocimiento.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listcampodetallado':
                try:
                    campoespecifico = request.GET.get('campoespecifico')
                    listcampoespecifico = campoespecifico
                    if len(campoespecifico) > 1:
                        listcampoespecifico = campoespecifico.split(',')
                    querybase = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoespecifico).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'addtitulacionpos':
                try:
                    data['title'] = u'Adicionar titulación'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['idcarrera'])
                    form = TitulacionPersonaAdmisionPosgradoForm()
                    form.adicionar()
                    data['form2'] = form
                    template = get_template("interesadosmaestria/addtitulacionpos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'viewrequisitos':
                try:
                    data['programa'] = programa = ProgramaPac.objects.filter(carrera_id=request.GET['idcarrera'], status=True).last()
                    if programa:
                        funcionpac = programa.funcionsustantivadocenciapac_set.filter(status=True).last()
                        if funcionpac:
                            perfilingreso = funcionpac.detalleperfilingreso_set.filter(status=True).last()
                            if perfilingreso:  # si el perfil cuenta con experiencia
                                if perfilingreso.experiencia:
                                    maestriaconexperiencia = True
                                    data['cantexperiencia'] = cantexperiencia = perfilingreso.cantidadexperiencia
                                if perfilingreso.alltitulos:
                                    data['alltitulos'] = aplicamaestria = True
                                else:
                                    # todos los campos especificos de los titulos de perfil
                                    data['listcetituloperfil'] = listcetituloperfil = CamposTitulosPostulacion.objects.filter(titulo__in=perfilingreso.titulo.all()).distinct()
                                    ca = 'Campo Amplio: '
                                    ce = 'Campo Específico: '
                                    cd = 'Campo Detallado: '
                                    if listcetituloperfil:
                                        for lista in listcetituloperfil:
                                            for campoa in lista.campoamplio.all():
                                                 ca = ca + campoa.__str__() + ' | '
                                            data['ca'] = ca
                                            for campoe in lista.campoespecifico.all():
                                                ce = ce + campoe.__str__() + ' | '
                                            data['ce'] = ce
                                            for campod in lista.campodetallado.all():
                                                cd = cd + campod.__str__() + ' | '
                                            data['cd'] = cd

                    template = get_template("interesadosmaestria/requisitosaplicarmaestria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'sugerirmaestrias':
                try:
                    hoy = datetime.now().date()
                    titulacion = Titulacion.objects.get(pk=request.GET['idt'], status=True) #PARA VALIDAr si los ce de la titulacion del post. esta en la de cohortemaestria(instauracion)
                    maecarrera = Carrera.objects.get(pk=request.GET['idc'], status=True)
                    listcarreranoaplica = []
                    listcarreranoaplica.append(maecarrera.id)
                    carrerasprogramainst = ProgramaPac.objects.values_list('carrera').filter(status=True)
                    cohortemaestria = CohorteMaestria.objects.values_list('maestriaadmision__carrera').filter(fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exclude(maestriaadmision__carrera=maecarrera)
                    for maestria in cohortemaestria:
                        if maestria in carrerasprogramainst:
                            aplicamaestria = False
                            listcetituloperfil = []
                            listcetitulopos = []
                            maestriaconexperiencia = False
                            cantexperiencia = 0
                            experienciamaestria = 0
                            programa = ProgramaPac.objects.filter(carrera_id=maestria, status=True).last()
                            if programa:
                                funcionpac = programa.funcionsustantivadocenciapac_set.filter(status=True).last()
                                if funcionpac:
                                    perfilingreso = funcionpac.detalleperfilingreso_set.filter(status=True).last()
                                    if perfilingreso: #si el perfil cuenta con experiencia
                                        if perfilingreso.experiencia:
                                            maestriaconexperiencia = True
                                            cantexperiencia = perfilingreso.cantidadexperiencia
                                        if perfilingreso.alltitulos:
                                            aplicamaestria = True
                                        else:
                                            # todos los campos especificos de los titulos de perfil
                                            listcetituloperfil = CamposTitulosPostulacion.objects.values_list('campoespecifico').filter(titulo__in=perfilingreso.titulo.all()).distinct()

                                    # todos los campos especificos del titulo del postulante
                                    listcetitulopos = CamposTitulosPostulacion.objects.values_list('campoespecifico').filter(titulo=titulacion.titulo).distinct()
                                    # consultar si el ce del postulante consta en el perfil de la maestria
                                    for ce in listcetitulopos:
                                        if ce in listcetituloperfil:
                                            aplicamaestria = True
                                    if not aplicamaestria:
                                        listcarreranoaplica.append(programa.carrera.id)
                                else:
                                    listcarreranoaplica.append(maestria)
                        else:
                            listcarreranoaplica.append(maestria)
                    cohortemaestria = CohorteMaestria.objects.filter(fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exclude(maestriaadmision__carrera_id__in=listcarreranoaplica)
                    if cohortemaestria:
                        data['maestria'] = cohortemaestria
                        template = get_template("interesadosmaestria/sugerenciasmaestrias.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": 'sinmaestriaaplicable', 'mensaje':'Lo sentimos, la Universidad Estatal de Milagro no está ofertando Maestrías acorde a su título. Intente seleccionando otra titulación.'})
                except Exception as ex:
                    pass

            if action == 'inscripcion':
                try:
                    data['title'] = u'Registro Admisión-MAESTRÍAS'
                    return render(request, "interesadosmaestria/interesadosmaestria.html", data)
                except Exception as ex:
                    pass

            if action == 'recursos':
                try:
                    data['title'] = u'Listado de compendios y videos magistrales'
                    codigomateria = request.GET['id']
                    data['nomasignatura'] = nomasignatura = Materia.objects.get(pk=codigomateria)
                    existecompendiosemanal = True
                    existevideossemanal = True
                    detallesilabosemanal = DetalleSilaboSemanalTema.objects.values_list('silabosemanal_id', flat=True).filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=[1,2],silabosemanal__silabo__materia=nomasignatura,status=True)
                    listacompendios = CompendioSilaboSemanal.objects.filter(silabosemanal_id__in=detallesilabosemanal,silabosemanal__silabo__materia=nomasignatura,silabosemanal__status=True,status=True).exclude(estado_id=3).order_by('id')
                    # if not listacompendios:
                    listacompendiosplananalito = RecursoTemaProgramaAnalitico.objects.filter(tema__unidadresultadoprogramaanalitico__orden__in=[1,2],tema__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla__asignatura=nomasignatura.asignaturamalla.asignatura,status=True).exclude(estado=3).order_by('tema__unidadresultadoprogramaanalitico__orden')
                    existecompendiosemanal = False
                    data['listadocompendio'] = listacompendios
                    data['listacompendiosplananalito'] = listacompendiosplananalito
                    data['existecompendiosemanal'] = existecompendiosemanal
                    listavideos = VideoMagistralSilaboSemanal.objects.filter(silabosemanal_id__in=detallesilabosemanal,silabosemanal__silabo__materia=nomasignatura,silabosemanal__status=True,status=True).exclude(estado_id=3).order_by('id')
                    if not listavideos:
                        listavideos = VideoTemaProgramaAnalitico.objects.filter(tema__unidadresultadoprogramaanalitico__orden__in=[1,2],tema__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla__asignatura=nomasignatura.asignaturamalla.asignatura,status=True).exclude(estado=3).order_by('tema__unidadresultadoprogramaanalitico__orden')
                        listasubvideos = VideoSubTemaProgramaAnalitico.objects.filter(subtema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=[1,2],subtema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla__asignatura=nomasignatura.asignaturamalla.asignatura,status=True).exclude(estado=3).order_by('subtema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden')
                        data['listasubvideos'] = listasubvideos
                        existevideossemanal = False
                    data['listadovideos'] = listavideos
                    data['existevideossemanal'] = existevideossemanal
                    return render(request, "interesadosmaestria/recursos_v3.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirdocumentos':
                try:
                    data['title'] = u'Requisitos básicos para admisión'
                    data['inscripcion'] = inscripcion = PreInscripcion.objects.get(pk=int(encrypt(request.GET['id'])), enviocorreo=True)
                    data['detalle'] = detalle=inscripcion.evidenciasmaestrias_set.filter(status=True)[0] if inscripcion.evidenciasmaestrias_set.filter(status=True).exists() else None
                    if detalle:
                        initial=model_to_dict(detalle)
                        form = RegistroRequisitosMaestriaForm1(initial=initial)
                    else:
                        form = RegistroRequisitosMaestriaForm()
                    data['form'] = form
                    return render(request, "interesadosmaestria/requisitosmaestria.html", data)
                    # return render(request, "interesadosmaestria/subirdocumentos.html", data)
                    # return render(request, "interesadosmaestria/interesadosmaestria.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                from posgrado.models import Convenio
                data['title'] = u'Registrar certificado'
                hoy = datetime.now().date()
                puedeinscribirse = False
                tieneperfilingreso = False
                validatodotitulo = False
                if 'idp' in request.GET:
                    data['person'] = persona = Persona.objects.get(pk=int(request.GET['idp']))
                else:
                    data['person'] = 0
                if 'codigocarrera' in request.GET:
                    if Carrera.objects.filter(pk=encrypt(request.GET['codigocarrera'])).exists():
                        data['carrera'] = carrera = Carrera.objects.get(pk=encrypt(request.GET['codigocarrera']))
                        data['maestria'] = MaestriasAdmision.objects.get(carrera__id=carrera.id)
                        if carrera.malla():
                            if carrera.malla().tiene_itinerario_malla_especialidad():
                                data['itinerarios'] = ItinerarioMallaEspecilidad.objects.filter(status=True,malla__id=carrera.malla().id)

                        if FormatoCarreraIpec.objects.values('id').filter(carrera_id=carrera, status=True).exists():
                            formatocorreo = FormatoCarreraIpec.objects.filter(carrera=carrera, status=True)[0]
                            if formatocorreo.banner and formatocorreo.banner.url:
                                data['banneradjunto'] = formatocorreo.download_banner()
                        #valida si el programa tiene registrado perfil de ingreso en instauacion.
                        if ProgramaPac.objects.values('id').filter(carrera=carrera, status=True).exists():
                            programapac = ProgramaPac.objects.filter(carrera=carrera, status=True).last()
                            if programapac.funcionsustantivadocenciapac_set.values('id').filter(status=True).exists():
                                funcion = programapac.funcionsustantivadocenciapac_set.filter(status=True).last()
                                if funcion.detalleperfilingreso_set.values('id').filter(status=True).exists():
                                    tieneperfilingreso = True
                                    validatodotitulo = funcion.detalleperfilingreso_set.filter(status=True).last().alltitulos

                        if CohorteMaestria.objects.values('id').filter(maestriaadmision__carrera=carrera,fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                            puedeinscribirse = True
                            data['cohorte'] = cohortem = CohorteMaestria.objects.filter(maestriaadmision__carrera=carrera, status=True, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy)[0]
                            if int(cohortem.valorprograma) > 0:
                                data['inversion'] = int(cohortem.valorprograma)
                            elif int(cohortem.valorprogramacertificado) > 0:
                                data['inversion'] = int(cohortem.valorprogramacertificado)
                            else:
                                data['inversion'] = 'Por definir'
                            x = cohortem.fechafincohorte - cohortem.fechainiciocohorte
                            data['duracion'] = (cohortem.fechafincohorte.year - cohortem.fechainiciocohorte.year) * 12 + cohortem.fechafincohorte.month - cohortem.fechainiciocohorte.month
                data['tieneperfilingreso'] = tieneperfilingreso
                data['validatodotitulo'] = validatodotitulo
                data['listacontacto'] = CONTACTO_MAESTRIA
                data['puedeinscribirse'] = puedeinscribirse
                data['tipodescuento'] = DetalleConfiguracionDescuentoPosgrado.objects.filter(configuraciondescuentoposgrado__tipo=2).order_by('id')
                data['canales'] = CanalInformacionMaestria.objects.filter(status=True, valido_form=True)
                data['convenios'] = Convenio.objects.filter(status=True, valido_form=True)
                return render(request, "alu_requisitosmaestria/admisionpos.html", data)
                # return render(request, "alu_requisitosmaestria/admision.html", data)
            except Exception as ex:
                pass
