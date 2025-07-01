# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse,HttpResponse
import random
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ProveedorForm, CongresoForm, InscritoCongresoForm, TipoParticipanteForm, \
    TipoParticipacionCongresoForm, TemaPonenciaForm
from sagest.models import Proveedor, Congreso, TipoParticipante, TipoParticipacionCongreso, InscritoCongreso, Rubro, \
    TipoOtroRubro
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre
from django.forms.models import model_to_dict
from datetime import datetime, date, timedelta
from settings import PUESTO_ACTIVO_ID, EMAIL_DOMAIN, EMAIL_INSTITUCIONAL_AUTOMATICO, SITE_STORAGE, DEBUG
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado, \
    conviert_html_to_pdfsave, conviert_html_to_pdfsaveqrcertificadoscongresoinscrito, \
    conviert_html_to_pdfsaveqrcertificadoscongresoinscritoturistica
from sga.models import CUENTAS_CORREOS, Provincia,Persona,Externo,Matricula,Graduado
from sga.tasks import send_html_mail, conectar_cuenta
from xlwt import *
from xlwt import easyxf
import xlwt
import json
import os
import pyqrcode
@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addcongreso':
            try:
                f = CongresoForm(request.POST , request.FILES)
                if 'imagencertificado' in request.FILES:
                    d = request.FILES['imagencertificado']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.jpg' or ext == '.jpeg' or ext == '.png':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .jpeg, .png"})
                    if d.size > 12582912:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf"})
                    if d.size > 12582912:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                if f.is_valid():
                    congreso = Congreso(tiporubro=f.cleaned_data['tiporubro'],
                                          nombre=f.cleaned_data['nombre'],
                                          fechainicio=f.cleaned_data['fechainicio'],
                                          fechafin=f.cleaned_data['fechafin'],
                                          fechainicioinscripcion=f.cleaned_data['fechainicioinscripcion'],
                                          fechafininscripcion=f.cleaned_data['fechafininscripcion'],
                                          cupo=f.cleaned_data['cupo'],
                                          visualizar=f.cleaned_data['visualizar'],
                                          gratuito=f.cleaned_data['gratuito'],
                                        )

                    congreso.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        congreso.archivo = newfile
                        congreso.save(request)
                    if 'imagencertificado' in request.FILES:
                        newfile = request.FILES['imagencertificado']
                        congreso.imagencertificado = newfile
                        congreso.save(request)

                    log(u'Adiciono nuevo congreso: %s' % congreso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcongreso':
            try:
                congreso = Congreso.objects.get(pk=request.POST['id'])
                f = CongresoForm(request.POST, request.FILES)
                if 'imagencertificado' in request.FILES:
                    d = request.FILES['imagencertificado']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.jpg' or ext == '.jpeg' or ext == '.png':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .jpeg, .png"})
                    if d.size > 12582912:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf"})
                    if d.size > 12582912:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                if f.is_valid():
                    congreso.tiporubro = f.cleaned_data['tiporubro']
                    congreso.nombre = f.cleaned_data['nombre']
                    congreso.fechainicio = f.cleaned_data['fechainicio']
                    congreso.fechafin = f.cleaned_data['fechafin']
                    congreso.fechainicioinscripcion = f.cleaned_data['fechainicioinscripcion']
                    congreso.fechafininscripcion = f.cleaned_data['fechafininscripcion']
                    congreso.cupo = f.cleaned_data['cupo']
                    congreso.visualizar = f.cleaned_data['visualizar']
                    congreso.gratuito = f.cleaned_data['gratuito']
                    congreso.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        congreso.archivo = newfile
                        congreso.save(request)
                    if 'imagencertificado' in request.FILES:
                        newfile = request.FILES['imagencertificado']
                        congreso.imagencertificado = newfile
                        congreso.save(request)
                    log(u'Modificó proveedor: %s' % congreso, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecongreso':
            try:
                congreso = Congreso.objects.get(pk=request.POST['id'])
                if congreso.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"El congreso no se puede eliminar por uso."})
                log(u'Eliminó congreso: %s' % congreso, request, "del")
                congreso.status=False
                congreso.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delinscrito':
            try:
                inscribir = InscritoCongreso.objects.get(pk=int(request.POST['id']))

                if inscribir.cancelo_rubro():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el inscrito ya cuenta rubros cancelados."})
                log(u'Elimino Incrito de congreso : %s [%s]' % (inscribir,inscribir.id), request, "del")
                inscribir.delete()
                if inscribir.congreso.tiporubro:
                    if Rubro.objects.filter(persona=inscribir.participante,tipo=inscribir.congreso.tiporubro,cancelado=False, status=True).exists():
                        listarubros = Rubro.objects.filter(persona=inscribir.participante,tipo=inscribir.congreso.tiporubro,cancelado=False, status=True)
                        for rubro in listarubros:
                            rubro.status=False
                            rubro.save(request)
                            log(u'Elimino Rubro en congreso : %s [%s]' % (inscribir, inscribir.congreso), request, "del")
                            if rubro.epunemi and rubro.idrubroepunemi > 0:
                                cursor = connections['epunemi'].cursor()
                                sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id=" + str(
                                    rubro.idrubroepunemi)
                                cursor.execute(sql)
                                cursor.close()

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'reporte_certificadoprevio':
            try:
                inscrito = InscritoCongreso.objects.get(pk=int(request.POST['id']))
                data['congreso'] = congreso = inscrito.congreso
                data['inscrito'] = inscrito
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"Milagro, %s de %s del %s" % ( datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                qrname = 'qr_certificado_' + str(inscrito.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'certificadoscongresoinscrito', ''))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/certificadoscongresoinscrito/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = qrname
                return conviert_html_to_pdfsaveqrcertificadoscongresoinscrito(
                    'congreso/certificado_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje":"%s"%ex})

        elif action == 'reporte_certificado':
            try:
                inscrito = InscritoCongreso.objects.get(pk=int(request.POST['id']))
                data['congreso'] = congreso = inscrito.congreso
                data['elabora_persona'] = persona
                data['inscrito'] = inscrito
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre","octubre", "noviembre", "diciembre"]
                data['fecha'] =  u"Milagro, %s de %s del %s" % (datetime.now().day, str(mes[datetime.now().month - 1]),datetime.now().year)
                qrname = 'qr_certificado_' + str(inscrito.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'certificadoscongresoinscrito', ''))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)

                url = pyqrcode.create('http://sga.unemi.edu.ec//media/certificadoscongresoinscrito/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                valida = conviert_html_to_pdfsaveqrcertificadoscongresoinscrito(
                    'congreso/certificado_pdf.html',
                    {'pagesize': 'A4', 'data': data},qrname + '.pdf'
                )
                if valida:
                    os.remove(rutaimg)
                    inscrito.rutapdf = '/certificadoscongresoinscrito/' + qrname + '.pdf'
                    inscrito.emailnotificado = True
                    inscrito.fecha_emailnotifica = datetime.now().date()
                    inscrito.persona_emailnotifica = persona
                    inscrito.save(request)
                    # lista=[]
                    # lista.append('jussibethtatianaplaces@gmail.com')
                    asunto = u"CERTIFICADO - " + inscrito.congreso.nombre
                    send_html_mail(asunto, "emails/notificar_certificado_congreso.html",
                                   {'sistema': request.session['nombresistema'], 'inscrito': inscrito },
                                   inscrito.participante.emailpersonal(), [], [inscrito.rutapdf],
                                   cuenta=CUENTAS_CORREOS[0][1])

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje":"%s"%ex})


        elif action == 'certificado_congreso_turistico':
            with transaction.atomic():
                try:
                    inscrito = InscritoCongreso.objects.get(pk=int(request.POST['id']))
                    ahora = datetime.now()
                    data['congreso'] = congreso = inscrito.congreso.nombre
                    data['elabora_persona'] = persona
                    data['inscrito'] = inscrito
                    data['fecha_actual'] = ahora
                    documento = inscrito.participante.cedula if not inscrito.participante.cedula is None else inscrito.participante.pasaporte
                    url_path = 'http://127.0.0.1:8000'
                    if not DEBUG:
                        url_path = 'https://sga.unemi.edu.ec'
                    # folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'certificadoscongresoinscrito', ''))
                    folder_certificado = os.path.join(
                        os.path.join(SITE_STORAGE, 'media', 'certificadoscongresoinscrito',documento, str(ahora.year),
                                     f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf', ''))
                    folder_qrcode = os.path.join(
                        os.path.join(SITE_STORAGE, 'media', 'certificadoscongresoinscrito', documento, str(ahora.year),
                                     f'{ahora.month:02d}', f'{ahora.day:02d}', 'qrcode', ''))

                    fileName = f'{documento}'

                    ruta_img = folder_qrcode + fileName + '.png'
                    ruta_pdf = folder_certificado + fileName + '.pdf'

                    url_pdf = f'{url_path}/media/certificadoscongresoinscrito/{documento}/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/pdf/{fileName}.pdf'
                    url_png = f'{url_path}/media/certificadoscongresoinscrito/{documento}/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/qrcode/{fileName}.png'

                    if os.path.isfile(ruta_pdf):
                        os.remove(ruta_pdf)
                    elif os.path.isfile(ruta_img):
                        os.remove(ruta_img)
                    os.makedirs(folder_certificado, exist_ok=True)
                    os.makedirs(folder_qrcode, exist_ok=True)

                    firma = f'Documento: {url_pdf} \nGenerado en: https://sga.unemi.edu.ec'.encode(
                        'utf-8')
                    url = pyqrcode.create(firma, encoding='iso-8859-1', mode='binary')
                    imagen_qr = url.png(ruta_img, scale=16, module_color=[0, 0, 0, 128], background=[255, 248, 220])

                    data['imagen_qr'] = url_png
                    data['version'] = ahora.strftime('%Y%m%d_%H%M%S')
                    data['firma_rector_unemi'] = f'{url_path}/static/images/firmasdigitales/firma_fabricio_guevara.png'
                    data['firma_rector_fhd'] = f'{url_path}/static/images/firmasdigitales/firma_christoph_scholz.png'
                    data['firma_vicerrectora'] = f'{url_path}/static/images/firmasdigitales/firma_jesennia_cardenas.png'
                    data['firma_director_turismo'] = f'{url_path}/static/images/firmasdigitales/firma_antonio_roldan.png'
                    result = conviert_html_to_pdfsaveqrcertificadoscongresoinscritoturistica(
                        'congreso/certificado_congreso_turistica.html',
                        {'pagesize': 'A4', 'data': data}, folder_certificado, fileName + '.pdf'
                    )
                    isSuccess = result.get('isSuccess', False)
                    if not isSuccess:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar certificado."})


                    filepdf = result.get('data',{}).get('filepdf',{}).name

                    inscrito.rutapdf = url_pdf
                    inscrito.save(request)
                    lista=[]
                    lista.append('jvaldezj@unemi.edu.ec')
                    # lista.append('jplacesc@unemi.edu.ec')
                    asunto = u"CERTIFICADO - " + inscrito.congreso.nombre
                    send_html_mail(asunto, "emails/notificar_certificado_congreso.html",
                                   {'sistema': 'Sistema de Gestión Académica', 'inscrito': inscrito},
                                   inscrito.participante.emailpersonal(), lista, [filepdf],
                                   cuenta=CUENTAS_CORREOS[0][1])

                    inscrito.emailnotificado =True
                    inscrito.save(request)

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback()
                    return JsonResponse({"result": "bad", "mensaje": "%s" % ex})




        elif action == 'addregistro':
            try:
                hoy = datetime.now().date()
                cedula = request.POST['cedula'].strip()
                tipoiden = request.POST['id_tipoiden']
                telefono = request.POST['telefono']
                nombres = request.POST['nombres']
                apellido1 = request.POST['apellido1']
                apellido2 = request.POST['apellido2']
                email = request.POST['email']
                sexo = request.POST['genero']
                id_participaciones = request.POST['id_participaciones']
                participacion = TipoParticipacionCongreso.objects.get(status=True, id=id_participaciones)
                costo_curso_total = participacion.valor
                congreso = Congreso.objects.get(pk=request.POST['cursoid'])
                if not congreso.tiporubro:
                    return JsonResponse({'result': 'bad', "mensaje": u"No existe Rubro en curso."})
                tiporubroarancel = congreso.tiporubro
                if Persona.objects.filter(cedula=cedula).exists():
                    datospersona = Persona.objects.get(cedula=cedula)
                elif Persona.objects.filter(pasaporte=cedula).exists():
                    datospersona = Persona.objects.get(pasaporte=cedula)
                if datospersona:
                    datospersona = Persona.objects.filter(Q(cedula__icontains=cedula) | Q(pasaporte__icontains=cedula))[0]
                    datospersona.email = email
                    datospersona.telefono = telefono
                    datospersona.save(request)
                    if not InscritoCongreso.objects.filter(participante=datospersona, congreso=congreso,
                                                           status=True).exists():
                        inscripcioncurso = InscritoCongreso(participante=datospersona,
                                                            congreso=congreso,
                                                            tipoparticipacion=participacion,
                                                            observacion="Inscrito el %s" % hoy
                                                            )
                        inscripcioncurso.save(request)
                        fechamaxpago = datetime.now().date() + timedelta(days=3)
                        rubro = Rubro(tipo=tiporubroarancel,
                                      persona=datospersona,
                                      congreso=congreso,
                                      relacionados=None,
                                      nombre=tiporubroarancel.nombre + ' - ' + congreso.nombre,
                                      cuota=1,
                                      fecha=datetime.now().date(),
                                      fechavence=fechamaxpago,
                                      valor=costo_curso_total,
                                      iva_id=1,
                                      valoriva=0,
                                      valortotal=costo_curso_total,
                                      saldo=costo_curso_total,
                                      epunemi=True,
                                      observacion=participacion.nombre_completo(),
                                      cancelado=False)
                        rubro.save(request)
                        return JsonResponse({'result': 'ok',
                                         "mensaje": u"Estimado participante, Usted se encuentra correctamente inscrito.",
                                         "aviso": u"{} se encuentra correctamente inscrito.".format(
                                             datospersona.nombre_completo())})
                    else:
                        return JsonResponse(
                            {'result': 'si', "mensaje": u"Usted ya se encuentra matriculado en el congreso.",
                             "mensaje": u"{} ya se encuentra matriculado en el congreso.".format(
                                 datospersona.nombre_completo())})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'consultacedula':
            try:
                codigocurso = Congreso.objects.get(pk=request.POST['codigocurso'])
                cedula = request.POST['cedula'].strip()
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
                if Persona.objects.filter(cedula=cedula).exists():
                    datospersona = Persona.objects.get(cedula=cedula)
                elif Persona.objects.filter(pasaporte=cedula).exists():
                    datospersona = Persona.objects.get(pasaporte=cedula)
                if datospersona:
                    if datospersona.sexo:
                        idgenero = datospersona.sexo.id
                    if datospersona.provincia:
                        provinciaid = datospersona.provincia.id
                    if datospersona.canton:
                        cantonid = datospersona.canton.id
                        cantonnom = datospersona.canton.nombre
                    if datospersona.externo_set.filter(status=True).exists():
                        datospersonaexterna = datospersona.externo_set.filter(status=True)[0]
                        lugarestudio = datospersonaexterna.lugarestudio
                        carrera = datospersonaexterna.carrera
                        profesion = datospersonaexterna.profesion
                        institucionlabora = datospersonaexterna.institucionlabora
                        cargo = datospersonaexterna.cargodesempena
                        teleoficina = datospersonaexterna.telefonooficina
                    if not InscritoCongreso.objects.filter(participante=datospersona, congreso=codigocurso,
                                                           status=True).exists():
                        return JsonResponse(
                            {"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                             "nombres": datospersona.nombres, "email": datospersona.email,
                             "telefono": datospersona.telefono,
                             "direccion1": datospersona.direccion, "direccion2": datospersona.direccion2,
                             "nacimiento": datospersona.nacimiento,
                             "provinciaid": provinciaid, "cantonid": cantonid, "cantonnom": cantonnom,
                             "lugarestudio": lugarestudio, "carrera": carrera, "profesion": profesion,
                             "institucionlabora": institucionlabora, "cargo": cargo, "teleoficina": teleoficina,
                             "idgenero": idgenero, "habilitaemail": 1})
                    else:
                        miinscripcion = InscritoCongreso.objects.get(participante=datospersona, congreso=codigocurso,
                                                                     status=True)
                        return JsonResponse({"result": "si",
                                             "mensaje": u"Usted ya se encuentra inscrito en el curso: </br>" + codigocurso.nombre + ' - ' + miinscripcion.observacion,
                                             "aviso": u"{} ya se encuentra inscrito en el curso: </br>".format(
                                                 datospersona.nombre_completo()) + codigocurso.nombre + ' - ' + miinscripcion.observacion})
                else:
                    return JsonResponse({"result": "no"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verificaparticipacion':
            try:
                codigocurso = Congreso.objects.get(pk=request.POST['id'])
                participaciones = TipoParticipacionCongreso.objects.filter(status=True, congreso=codigocurso)
                lista = []
                for part in participaciones:
                    lista.append([part.id, part.nombre_completo()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'validarparticipacion':
            try:
                participacion = request.POST['participacion'].strip()
                participacion = TipoParticipacionCongreso.objects.get(status=True, id=participacion)
                if participacion.tipoparticipante_id in [2, 4, 5, 10, 11]:
                    cedula = request.POST['cedula'].strip()
                    datospersona = None
                    if Persona.objects.filter(cedula=cedula, status=True).exists():
                        datospersona = Persona.objects.get(cedula=cedula, status=True)
                    elif Persona.objects.filter(pasaporte=cedula, status=True).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula, status=True)
                    if not datospersona:
                        return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como usuario de UNEMI",
                                             "aviso": "No consta como usuario de UNEMI"})
                    else:
                        # DOCENTES
                        if participacion.tipoparticipante_id in [4, 10]:
                            if not datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True,
                                                                               regimenlaboral__id=2).exists():
                                return JsonResponse(
                                    {"result": "bad", "costocurso": "Ud, no consta como docente de UNEMI",
                                     "aviso": "No consta como docente de UNEMI"})
                        elif participacion.tipoparticipante_id in [2, 11]:
                            if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(
                                    status=True).exclude(coordinacion_id=9)
                                if not Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True,
                                                                cerrada=False).exists():
                                    return JsonResponse({"result": "bad",
                                                         "costocurso": "Ud, no consta con una matrícula activa en UNEMI",
                                                         "aviso": "No consta con una matrícula activa en UNEMI"})
                            else:
                                return JsonResponse(
                                    {"result": "bad", "costocurso": "Ud, no consta con una matrícula activa en UNEMI",
                                     "aviso": "No consta con una matrícula activa en UNEMI"})
                        elif participacion.tipoparticipante_id == 5:
                            if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(
                                    status=True).exclude(coordinacion_id=9)
                                if not Graduado.objects.filter(inscripcion__id__in=verificainsripcion,
                                                               status=True).exists():
                                    return JsonResponse(
                                        {"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI",
                                         "aviso": "No consta como graduado de UNEMI"})
                            else:
                                return JsonResponse(
                                    {"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI",
                                     "aviso": "No consta como graduado de UNEMI"})
                return JsonResponse({"result": "ok", "costocurso": participacion.valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addtipoparticipante':
            try:
                f = TipoParticipanteForm(request.POST)
                if f.is_valid():
                    if not TipoParticipante.objects.filter(status=True,
                                                      nombre=f.cleaned_data['nombre'].upper()).exists():
                        tipoparticipante = TipoParticipante(nombre=f.cleaned_data['nombre'])
                        tipoparticipante.save(request)
                        log(u'Adiciono Tipo de participante: %s' % tipoparticipante.nombre, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittipoparticipante':
            try:
                tipoparticipante = TipoParticipante.objects.get(pk=request.POST['id'])
                f = TipoParticipanteForm(request.POST)
                if f.is_valid():
                    if not TipoParticipante.objects.filter(status=True,
                                                      nombre=f.cleaned_data['nombre'].upper()).exclude(
                            pk=request.POST['id']).exists():
                        tipoparticipante.nombre = f.cleaned_data['nombre']
                        tipoparticipante.save(request)
                        log(u'Modificó Tipo de Participante: %s' % tipoparticipante, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletetipoparticipante':
            try:
                tipoparticipante = TipoParticipante.objects.get(pk=request.POST['id'])
                tipoparticipante.status = False
                tipoparticipante.save(request)
                log(u'Edito el estado de Tipo de Participante: %s' % tipoparticipante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addtema':
            try:
                inscritocongreso = InscritoCongreso.objects.get(pk=int(request.POST['id']))
                f = TemaPonenciaForm(request.POST)
                if f.is_valid():
                        # inscrito = InscritoCongreso(tema=f.cleaned_data['tema'] )
                        inscritocongreso.tema = f.cleaned_data['tema'].upper()
                        inscritocongreso.save(request)
                        log(u'Adiciono tema ponencia: %s' % inscritocongreso, request, "add")
                        return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addparticipacioncongreso':
            try:
                f = TipoParticipacionCongresoForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.jpg' or  ext == '.jpeg' or ext == '.png':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .jpeg, .png"})
                    if d.size > 12582912:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                if f.is_valid():
                    if not TipoParticipacionCongreso.objects.filter(tipoparticipante=f.cleaned_data['tipoparticipante'],
                                                               congreso_id=request.POST['id'],
                                                               valor=f.cleaned_data['valor'], status=True).exists():
                        tipoparticipacion = TipoParticipacionCongreso(tipoparticipante=f.cleaned_data['tipoparticipante'],
                                                             congreso_id=request.POST['id'],
                                                             valor=f.cleaned_data['valor'])
                        tipoparticipacion.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            tipoparticipacion.imagencertificado = newfile
                            tipoparticipacion.save(request)
                        log(u'Adiciono tipo participación-congreso: %s' % tipoparticipacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Ya existe un registro con los datos ingresados."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editparticipacioncongreso':
            try:
                tipoparticipacion = TipoParticipacionCongreso.objects.get(pk=request.POST['id'])

                f = TipoParticipacionCongresoForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.jpg' or  ext == '.jpeg' or ext == '.png':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .jpeg, .png"})
                    if d.size > 12582912:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                if f.is_valid():
                    if not TipoParticipacionCongreso.objects.filter(tipoparticipante=f.cleaned_data['tipoparticipante'],
                                                               congreso=tipoparticipacion.congreso,
                                                               valor=f.cleaned_data['valor'],status=True).exclude(pk=request.POST['id']).exists():
                        tipoparticipacion.tipoparticipante=f.cleaned_data['tipoparticipante']
                        tipoparticipacion.valor=f.cleaned_data['valor']
                        tipoparticipacion.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            tipoparticipacion.imagencertificado = newfile
                            tipoparticipacion.save(request)
                        log(u'Modificó tipo participación-congreso: %s' % tipoparticipacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Ya existe un registro con los datos ingresados en este congreso."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteparticipacioncongreso':
            try:
                tipoparticipacion = TipoParticipacionCongreso.objects.get(pk=request.POST['id'])
                log(u'Eliminó participación congreso: %s' % tipoparticipacion, request, "del")
                tipoparticipacion.status=False
                tipoparticipacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'bloqueopublicacion':
            try:
                evento = Congreso.objects.get(pk=request.POST['id'])
                evento.visualizar = True if request.POST['val'] == 'y' else False
                evento.save(request)
                log(u'Visualiza o no en Congreso : %s (%s)' % (evento, evento.visualizar),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'aplicatemaponencia':
            try:
                participacion = TipoParticipacionCongreso.objects.get(pk=request.POST['id'])
                participacion.tienetema = True if request.POST['val'] == 'y' else False
                participacion.save(request)
                log(u'Aplica o no tema : %s (%s)' % (participacion, participacion.tienetema),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addcongreso':
                try:
                    data['title'] = u'Adicionar Congreso'
                    data['form'] = CongresoForm()
                    return render(request, "congreso/addcongreso.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcongreso':
                try:
                    data['title'] = u'Editar Congreso'
                    data['congreso'] = congreso = Congreso.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(congreso)
                    form = CongresoForm(initial=initial)
                    data['form'] = form
                    return render(request, "congreso/editcongreso.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletecongreso':
                try:
                    data['title'] = u'Borrar Congreso'
                    data['congreso'] = Congreso.objects.get(pk=request.GET['id'])
                    return render(request, "congreso/deletecongreso.html", data)
                except Exception as ex:
                    pass


            elif action == 'addtema':
                try:
                    data['title'] = u'Adicionar Tema - Ponencia '

                    data['inscrito'] = InscritoCongreso.objects.get(pk=int(request.GET['id']))
                    # data['inscrito']=int(request.GET['id'])
                    f = TemaPonenciaForm()
                    data['form'] = f
                    return render(request, 'congreso/addtemaponencia.html', data)
                except Exception as ex:
                    pass


            elif action == 'addparticipacioncongreso':
                try:
                    data['title'] = u'Adicionar Tipo Participación - Congreso'
                    data['id_congreso']=int(request.GET['id'])
                    f = TipoParticipacionCongresoForm()
                    data['form'] = f
                    return render(request, 'congreso/addparticipacioncongreso.html', data)
                except Exception as ex:
                    pass

            elif action == 'editparticipacioncongreso':
                try:
                    data['title'] = u'Editar Tipo Participación - Congreso'
                    data['tipoparticipacion'] = tipoparticipacion = TipoParticipacionCongreso.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(tipoparticipacion)
                    f = TipoParticipacionCongresoForm(initial=initial)
                    data['form'] = f
                    return render(request, 'congreso/editparticipacioncongreso.html', data)
                except Exception as ex:
                    pass

            elif action == 'deleteparticipacioncongreso':
                try:
                    data['title'] = u'Borrar Participación Congreso'
                    data['tipoparticipacion'] = TipoParticipacionCongreso.objects.get(pk=request.GET['id'])
                    return render(request, "congreso/deleteparticipacioncongreso.html", data)
                except Exception as ex:
                    pass


            elif action == 'inscritos':
                try:
                    data['title'] = u'Inscritos'
                    search = None
                    ids = None
                    url_vars = f'&action=inscritos&id=' + str(request.GET['id'])
                    data['congreso'] = congreso = Congreso.objects.get(pk=int(request.GET['id']))
                    inscrito = congreso.inscritocongreso_set.filter(status=True).distinct().order_by('participante__apellido1', 'participante__apellido2','participante__nombres')
                    data['tipoparticipacion'] = tipoparticipacion = TipoParticipacionCongreso.objects.filter(congreso=congreso, status=True)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += f'&s=' + search
                        if len(ss) == 1:
                            inscrito = inscrito.filter(Q(participante__nombres__icontains=search) |
                                                                                Q(participante__apellido1__icontains=search) |
                                                                                Q(participante__apellido2__icontains=search) |
                                                                                Q(participante__cedula__icontains=search) |
                                                                                Q(participante__pasaporte__icontains=search))

                        else:
                            inscrito = inscrito.filter((Q(participante__apellido1__icontains=ss[0]) & Q(
                                participante__apellido2__icontains=ss[1])) |
                                                                                (Q(participante__nombres__icontains=ss[0]) &
                                                                                 Q(participante__nombres__icontains=ss[1])))
                    if 'tipoparticipacion_id' in request.GET:
                        data['tipoparticipacion_id']=tipoparticipacion_id = int(request.GET['tipoparticipacion_id'].strip())
                        inscrito = inscrito.filter(tipoparticipacion_id=tipoparticipacion_id)

                    paging = MiPaginador(inscrito, 20)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['inscritos'] = page.object_list
                    hoy = datetime.now().date()
                    listacur = []
                    data['listaprovinvias'] = Provincia.objects.filter(pais_id=1, status=True).order_by('nombre')
                    data['reporte_0'] = obtener_reporte('reporte_inscritos_congreso_id')
                    data['reporte_1'] = obtener_reporte('reporte_inscritos_congreso_saldo_pendiente')
                    data['reporte_2'] = obtener_reporte('reporte_congreso_recaudacion')
                    data["url_vars"] = url_vars
                    return render(request, "congreso/inscritos.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinscrito':
                try:
                    data['title'] = u'Eliminar Inscrito'
                    data['inscrito'] = InscritoCongreso.objects.get(pk=int(request.GET['id']))
                    return render(request, "congreso/delinscrito.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscripcion':
                try:
                    data['title'] = u'Registrar certificado'
                    hoy = datetime.now().date()
                    cursos = None
                    listacur = []
                    if Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , visualizar=True, status=True).exists():
                        cursos = Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, visualizar=True, status=True)
                        for cur in cursos:
                            if cur.cupo > cur.inscritocongreso_set.filter(status=True).count():
                                listacur.append(cur.id)
                        if listacur:
                            cursos = Congreso.objects.filter(pk__in=listacur)
                        else:
                            cursos = None
                        if not TipoOtroRubro.objects.filter(pk__in=cursos.values_list('tiporubro_id').filter(status=True)).exists():
                            cursos = None
                    data['cursos'] = cursos
                    data['listaprovinvias'] = Provincia.objects.filter(pais_id=1, status=True).order_by('nombre')
                    return render(request, "inscripcionescongresos/inscripcionescongresos.html", data)
                except Exception as ex:
                    pass


            elif action == 'tipoparticipantes':
                try:
                    data['title'] = u'Tipo de Participantes'
                    url_vars = f"&action=tipoparticipantes"
                    if puede_realizar_accion(request, 'sagest.puede_gestionar_participacion_congresos'):
                        search = None
                        participantes = TipoParticipante.objects.filter(status=True)
                        if 's' in request.GET:
                            search = request.GET['s']
                            s = search.split(" ")
                            url_vars += 'f&s=' + search
                            if len(s) == 2:
                                participantes = participantes.filter(
                                    Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1]))
                            else:
                                participantes = participantes.filter(nombre__icontains=search)

                        paging = MiPaginador(participantes, 15)
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
                        data['page'] = page
                        data['rangospaging'] = paging.rangos_paginado(p)
                        data['tipoparticipantes'] = page.object_list
                        data['search'] = search if search else ""
                        data["url_vars"] = url_vars
                    return render(request, 'congreso/tipoparticipantes.html', data)
                except Exception as ex:
                    pass

            elif action == 'addtipoparticipante':
                try:
                    data['title'] = u'Adicionar Tipo de Participante'
                    form = TipoParticipanteForm()
                    data['form'] = form
                    return render(request, 'congreso/addtipoparticipante.html', data)
                except Exception as ex:
                    pass

            elif action == 'edittipoparticipante':
                try:
                    data['title'] = u'Editar Tipo de Participante'
                    data['tipoparticipante'] = tipoparticipante = TipoParticipante.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(tipoparticipante)
                    form = TipoParticipanteForm(initial=initial)
                    data['form'] = form
                    return render(request, 'congreso/edittipoparticipante.html', data)
                except Exception as ex:
                    pass

            elif action == 'deletetipoparticipante':
                try:
                    data['title'] = u'Eliminar Tipo de Participante'
                    data['tipoparticipante'] = TipoParticipante.objects.get(pk=request.GET['id'])
                    return render(request, 'congreso/deletetipoparticipante.html', data)
                except Exception as ex:
                    pass


            elif action == 'tipoparticipacioncongreso':
                try:
                    data['title'] = u'Tipo de Participación'
                    if  puede_realizar_accion(request, 'sagest.puede_gestionar_participacion_congresos'):
                        search = None
                        data['congreso'] = congreso = Congreso.objects.get(pk=int(request.GET['id']))
                        tipoparticipacion = TipoParticipacionCongreso.objects.filter(status=True, congreso=congreso)

                        if 's' in request.GET:
                            search = request.GET['s']
                            s = search.split(" ")
                            if len(s) == 2:
                                tipoparticipacion = tipoparticipacion.filter(Q(tipoparticipante__nombre__icontains=s[0]) | Q(tipoparticipante__nombre__icontains=s[1])|
                                                                     Q(congreso__nombre__icontains=s[0] )| Q(congreso__nombre__icontains=s[1]))
                            else:
                                tipoparticipacion = tipoparticipacion.filter(Q(tipoparticipante__nombre__icontains=search) | Q(congreso__nombre__icontains=search))
                        paging = MiPaginador(tipoparticipacion, 15)
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
                        data['page'] = page
                        data['rangospaging'] = paging.rangos_paginado(p)
                        data['tiposparticipacion'] = page.object_list
                        data['search'] = search if search else ""
                    return render(request, 'congreso/tipoparticipacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'reporteinscrito':
                try:
                    congreso = request.GET['id']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 4000),
                        (u"NOMBRE", 12000),
                        (u"CORREO", 12000),
                        (u"TELEFONO", 4000),
                        (u"CONGRESO", 20000),
                        (u"TIPO DE PARTICIPACION", 10000),
                        (u"OBSERVACION", 6000),
                        (u"ENLACE DEL CERTIFICADO", 6000)

                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 4
                    for inscrito in InscritoCongreso.objects.filter(status=True,congreso=congreso):
                        i = 0
                        campo1 = inscrito.participante.identificacion()
                        campo2 = str(inscrito.participante)
                        campo3 = inscrito.participante.emailpersonal()
                        campo4 = inscrito.participante.telefono
                        campo5 = inscrito.congreso.nombre
                        campo6 = str(inscrito.tipoparticipacion.tipoparticipante)
                        campo7 = str(inscrito.observacion)
                        campo8 = u"sga.unemi.edu.ec/media%s"%str(inscrito.rutapdf)

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, style1)

                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Gestión de congresos'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    congresos = Congreso.objects.filter(Q(nombre__icontains=search))
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    congresos = Congreso.objects.filter(id=ids)
                else:
                    congresos = Congreso.objects.filter(status=True).order_by('-fechainicioinscripcion')
                paging = MiPaginador(congresos, 20)
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
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['congresos'] = page.object_list
                return render(request, "congreso/view.html", data)
            except Exception as ex:
                pass
