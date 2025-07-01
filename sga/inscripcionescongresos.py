# -*- coding: latin-1 -*-
import json
import sys
from itertools import count
import random
from PIL.ImageOps import _lut
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db import transaction, connections
from django.db.models import Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.db.models.query_utils import Q
from datetime import datetime, timedelta, date
from xlwt import *
from xlwt import easyxf
import xlwt

from decorators import secure_module, last_access
from posgrado.forms import AdmiPeriodoForm
from sagest.models import TipoOtroRubro, Rubro, CapPeriodoIpec, CapEventoPeriodoIpec, CapInscritoIpec, Congreso, TipoParticipante, TipoParticipacionCongreso, InscritoCongreso, CuentaContable
from sga.commonviews import obtener_reporte
from sga.forms import ActextracurricularForm, RegistrarCertificadoForm, InscripcionCursoProsgradoForm, \
    CongresoXXISRRNetFormEN, InscripTuristicoForm, CongresoXXISRRNetFormES
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre
from sga.models import Persona, Provincia, Externo, Matricula, RecordAcademico, Graduado, miinstitucion, CUENTAS_CORREOS
from sga.templatetags.sga_extras import encrypt


from sga.tasks import send_html_mail, conectar_cuenta

# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addregistro':
                try:
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip()
                    tipoiden = request.POST['id_tipoiden']
                    telefono = request.POST['telefono']
                    tema = request.POST['tema']
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    email = request.POST['email']
                    sexo = request.POST['genero']
                    id_participaciones = request.POST['id_participaciones']
                    participacion = TipoParticipacionCongreso.objects.get(status=True, id=id_participaciones)

                    costo_curso_total=participacion.valor
                    congreso = Congreso.objects.get(pk=request.POST['cursoid'])
                    if congreso.cupo > congreso.inscritocongreso_set.filter(status=True).count():
                        if not congreso.tiporubro:
                            return JsonResponse({'result': 'bad', "mensaje": u"No existe Rubro en curso."})
                        tiporubroarancel = congreso.tiporubro
                        if tipoiden == '1':
                            if Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula),status=True)
                                if datospersona.count() > 1:
                                    raise NameError(
                                        u"La cedula ingresada se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona = datospersona[0]
                                datospersona.email = email
                                datospersona.telefono = telefono
                                datospersona.save(request)
                            else:
                                datospersona = Persona(cedula=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       telefono=telefono,
                                                       nacimiento=datetime.now().date()
                                                       )
                                datospersona.save(request)
                        if tipoiden == '2':
                            if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula), status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula),status=True)
                                if datospersona.count() > 1:
                                    raise NameError( u"El pasaporte ingresado se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona = datospersona[0]
                                datospersona.email = email
                                datospersona.telefono = telefono
                                datospersona.save(request)
                            else:
                                datospersona = Persona(pasaporte=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       telefono=telefono,
                                                       nacimiento=datetime.now().date()
                                                       )
                                datospersona.save(request)
                        if datospersona:
                            if not datospersona.externo_set.filter(status=True).exists():
                                datospersonaexterna = Externo(persona=datospersona,
                                                              nombrecomercial='',
                                                              nombrecontacto='',
                                                              )
                                datospersonaexterna.save(request)
                            if not InscritoCongreso.objects.filter(participante=datospersona, congreso=congreso, status=True).exists():
                                inscripcioncurso = InscritoCongreso(participante=datospersona,
                                                                   congreso=congreso,
                                                                    tipoparticipacion=participacion,
                                                                   observacion="Inscrito el %s"%hoy,
                                                                    tema = tema
                                                                   )
                                inscripcioncurso.save(request)
                                fechamaxpago = datetime.now().date() + timedelta(days=3)
                                if participacion.valor > 0:
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

                                # send_html_mail("Registro exitoso Inscripcion-CURSOS.", "emails/registroexito.html",
                                #                             #                {'sistema': u'CURSOS - UNEMI', 'fecha': datetime.now().date(),
                                #                             #                 'hora': datetime.now().time(), 'bs': browser, 'os': ops, 'cookies': cookies,
                                #                             #                 'screensize': screensize, 't': miinstitucion()}, datospersona.emailpersonal(), [],
                                #                             #                cuenta=variable_valor('CUENTAS_CORREOS')[4])
                            return JsonResponse({'result': 'ok', "mensaje": u"Estimado participante, Usted se encuentra correctamente inscrito/a.", "aviso": u"{} se encuentra correctamente inscrito.".format(datospersona.nombre_completo())})
                        else:
                            return JsonResponse({'result': 'si', "mensaje": u"{} ya se encuentra matriculado en el congreso.".format(datospersona.nombre_completo())})
                    else:
                        return JsonResponse({'result': 'bad', "mensaje": u"Lo sentimos el cupo está completo."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex}({sys.exc_info()[-1].tb_lineno})"})

            elif action == 'addxxisrrnet':
                try:
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    hoy = datetime.now().date()
                    idioma = request.POST.get('idioma', None)
                    provincia = None
                    if idioma == 'es':
                        form = CongresoXXISRRNetFormES(request.POST, request.FILES)
                    elif idioma == 'en':
                        form = CongresoXXISRRNetFormEN(request.POST, request.FILES)
                    else:
                        raise NameError("Ha ocurrido un problema, intentelo mas tarde")
                    if not form.is_valid(): raise NameError(f'{[{k:v[0]} for k,v in form.errors.items()]}')
                    if idioma == 'es': provincia = form.cleaned_data['provincia']
                    cedula = form.cleaned_data['documento']
                    tipoiden = form.cleaned_data['tipodocumento']
                    telefono = form.cleaned_data['telefono']
                    nombres = form.cleaned_data['nombres'] if idioma == 'es' else '-'
                    apellido1 = form.cleaned_data['apellido1']
                    apellido2 = form.cleaned_data['apellido2'] if idioma == 'es' else '-'
                    email = form.cleaned_data['email']
                    sexo = None if form.cleaned_data['genero'] in [3,4] else form.cleaned_data['genero']
                    participaciones = form.cleaned_data['tipoparticipante']
                    congreso = form.cleaned_data['congreso']
                    nombre_institucion = form.cleaned_data['nombreinstitucion']
                    orcid = None
                    pais = form.cleaned_data['pais']
                    archivo = None
                    costo_curso_total = participaciones.valor
                    hashed_password_ac ='ID'
                    usuario_log = ''
                    rubro = None
                    if not participaciones: raise NameError('Seleccione un tipo de participación válido/Select an Attendees valid')
                    if participaciones.tipoparticipante_id == 32:
                        if 'documentoinstitucion' not in request.FILES: raise NameError("Debe adjuntar un certificado institucional.")
                        archivo = request.FILES['documentoinstitucion']
                        ext = archivo.name.split('.')[-1].lower()
                        if ext not in ['pdf', 'jpg', 'png', 'jpeg']: raise NameError("Formato invalido del documento, tener en cuenta los siguientes formatos 'pdf', 'jpg', 'png', 'jpeg'")
                        if archivo.size > 10485760: raise NameError("El documento excede el limite de 10MB")
                        archivo.name = generar_nombre('certificadoinstitucional_', archivo.name)
                    existe_unemi = False
                    if congreso.cupo > congreso.inscritocongreso_set.filter(status=True).count():
                        tiporubroarancel = congreso.tiporubro
                        if tipoiden == '1':
                            if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula), status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula),status=True)
                                if datospersona.count() > 1:
                                    raise NameError(u"La cedula ingresada se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona = datospersona[0]
                                datospersona.email = email
                                datospersona.telefono = telefono
                                datospersona.save(request)
                                existe_unemi=True
                            else:
                                datospersona = Persona(cedula=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       telefono=telefono,
                                                       pais=pais,
                                                       provincia=provincia,
                                                       nacimiento=datetime.now().date()
                                                       )
                                datospersona.save(request)
                        if tipoiden == '2':
                            if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula), status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula), status=True)
                                if datospersona.count() > 1:
                                    raise NameError(u"El pasaporte ingresado se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona = datospersona[0]
                                datospersona.email = email
                                datospersona.telefono = telefono
                                datospersona.save(request)
                                existe_unemi=True
                            else:
                                datospersona = Persona(cedula=cedula,
                                                       pasaporte=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       telefono=telefono,
                                                       pais=pais,
                                                       provincia=provincia,
                                                       nacimiento=datetime.now().date()
                                                       )
                                datospersona.save(request)
                        if datospersona:
                            if not datospersona.externo_set.filter(status=True).exists():
                                datospersonaexterna = Externo(persona=datospersona,
                                                              nombrecomercial='',
                                                              nombrecontacto='',)
                                datospersonaexterna.save(request)
                            if not InscritoCongreso.objects.filter(participante=datospersona, congreso=congreso,status=True).exists():
                                inscripcioncurso = InscritoCongreso(participante=datospersona,
                                                                    congreso=congreso,
                                                                    tipoparticipacion=participaciones,
                                                                    observacion="Inscrito el %s" % hoy,
                                                                    nombreinstitucion=nombre_institucion,
                                                                    orcid=orcid,
                                                                    documentoinstitucion=archivo
                                                                    )
                                inscripcioncurso.save(request)
                                fechamaxpago = datetime.strptime('2024/04/01','%Y/%m/%d')
                                if participaciones.valor > 0:
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
                                                  observacion=participaciones.nombre_completo(),
                                                  cancelado=False)
                                    rubro.save(request)
                                    # -------CREAR PERSONA EPUNEMI-------
                                    cursor = connections['epunemi'].cursor()
                                    sql = """SELECT pe.id,pe.usuario_id FROM sga_persona AS pe WHERE (pe.cedula='%s') AND pe.status=TRUE;  """ % (
                                    datospersona.cedula)
                                    cursor.execute(sql)
                                    idalumno = cursor.fetchone()
                                    usuario_id = 'null'
                                    hashed_password = make_password(datospersona.cedula)
                                    hashed_password_ac=f'{datospersona.cedula}'
                                    usuario_log = f'{datospersona.usuario.username if datospersona.usuario else "N/A"}' if existe_unemi else f'{datospersona.cedula}'
                                    if idalumno is None:
                                        if existe_unemi:
                                            usuario_log = f'{datospersona.usuario.username}'
                                            sql = f"""
                                            SELECT us.id FROM auth_user us WHERE username = '{datospersona.usuario.username}';
                                            """
                                            cursor.execute(sql)
                                            usuario = cursor.fetchone()
                                            if usuario is None:
                                                sql = f"""
                                                INSERT INTO auth_user (username, password, email, first_name, last_name, is_active, is_staff, is_superuser)
                                                VALUES ('{datospersona.usuario.username}', '{hashed_password}', '', '', '', TRUE, FALSE, FALSE);
                                                """
                                                cursor.execute(sql)
                                                sql = f"""
                                                SELECT us.id FROM auth_user us WHERE username = '{datospersona.usuario.username}';
                                                """
                                                cursor.execute(sql)
                                                usuario_id = cursor.fetchone()
                                                usuario_id = usuario_id[0]
                                            else:
                                                usuario_id = usuario[0]
                                                sql = f"""
                                                UPDATE auth_user SET password = '{hashed_password}' WHERE id = {usuario_id}
                                                """
                                                cursor.execute(sql)
                                        else:
                                            usuario_log = f'{datospersona.cedula}'
                                            sql = f"""
                                            SELECT us.id FROM auth_user us WHERE username = '{datospersona.cedula}';
                                            """
                                            cursor.execute(sql)
                                            usuario = cursor.fetchone()
                                            if usuario is None:
                                                sql = f"""
                                                INSERT INTO auth_user (username, password, email, first_name, last_name, is_active, is_staff, is_superuser,date_joined)
                                                VALUES ('{datospersona.cedula}', '{hashed_password}', '', '', '', TRUE, FALSE, FALSE, NOW());
                                                """
                                                cursor.execute(sql)
                                                sql = f"""
                                                SELECT us.id FROM auth_user us WHERE username = '{datospersona.cedula}';
                                                """
                                                cursor.execute(sql)
                                                usuario_id = cursor.fetchone()
                                                usuario_id = usuario_id[0]
                                            else:
                                                usuario_id = usuario[0]
                                                sql = f"""
                                                UPDATE auth_user SET password = '{hashed_password}' WHERE id = {usuario_id}
                                                """
                                                cursor.execute(sql)
                                        sql = f""" INSERT INTO sga_persona (status,usuario_id, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                        nacimiento, tipopersona, direccion,
                                        telefono, email, contribuyenteespecial,
                                        anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                        regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                        tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                        acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                        idunemi, sector,direccion2,num_direccion,telefono_conv)
                                                VALUES(TRUE,{usuario_id}, '{datospersona.nombres}', '{datospersona.apellido1}', '{datospersona.apellido2}', '{datospersona.cedula}', '{datospersona.ruc}', '{datospersona.pasaporte}', '/{datospersona.nacimiento}/', {datospersona.tipopersona if datospersona.tipopersona else 1}, '{datospersona.direccion}', '{datospersona.telefono}', '{datospersona.email}',
                                                FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE,
                                                FALSE, FALSE, 0, '','','',''); """
                                        cursor.execute(sql)
                                        if datospersona.sexo:
                                            sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (datospersona.sexo.id)
                                            cursor.execute(sql)
                                            sexo = cursor.fetchone()
                                            if sexo is not None:
                                                sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], datospersona.cedula)
                                                cursor.execute(sql)
                                        if datospersona.pais:
                                            sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (
                                                datospersona.pais.id)
                                            cursor.execute(sql)
                                            pais = cursor.fetchone()

                                            if pais is not None:
                                                sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (
                                                pais[0], datospersona.cedula)
                                                cursor.execute(sql)
                                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (
                                        datospersona.cedula,
                                        datospersona.cedula,
                                        datospersona.cedula)
                                        cursor.execute(sql)
                                        idalumno = cursor.fetchone()
                                        alumnoepu = idalumno[0]
                                    else:
                                        alumnoepu = idalumno[0]
                                    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (
                                        rubro.tipo.id)
                                    cursor.execute(sql)
                                    registro = cursor.fetchone()
                                    # Si existe
                                    if registro is not None:
                                        tipootrorubro = registro[0]
                                    else:
                                        sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (
                                            rubro.tipo.tiporubro)
                                        cursor.execute(sql)
                                        centrocosto = cursor.fetchone()
                                        idcentrocosto = centrocosto[0]

                                        # Consulto la cuenta contable
                                        cuentacontable = CuentaContable.objects.get(partida=rubro.tipo.partida, status=True)
                                        # Creo el tipo de rubro en epunemi
                                        sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                                                           VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                            rubro.tipo.nombre, cuentacontable.partida.id, rubro.tipo.valor,
                                            rubro.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                            rubro.tipo.id)
                                        cursor.execute(sql)

                                        print(".:: Tipo de Rubro creado en EPUNEMI ::.")
                                        # Obtengo el id recién creado del tipo de rubro
                                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (
                                            rubro.tipo.id)
                                        cursor.execute(sql)
                                        registro = cursor.fetchone()
                                        tipootrorubro = registro[0]
                                    # pregunto si no existe rubro con ese id de unemi
                                    sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (
                                        rubro.id)
                                    cursor.execute(sql)
                                    registrorubro = cursor.fetchone()

                                    if registrorubro is None:
                                        # Creo nuevo rubro en epunemi
                                        sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                                    valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                                    idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                                    valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                                    titularcambiado, coactiva) 
                                                  VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                              % (
                                              alumnoepu, rubro.nombre, rubro.cuota, rubro.tipocuota, rubro.fecha, rubro.fechavence, rubro.saldo,
                                              rubro.saldo, rubro.iva_id, rubro.valoriva, rubro.valor,
                                              rubro.valortotal, rubro.cancelado, rubro.observacion, rubro.id, tipootrorubro,
                                              rubro.compromisopago if rubro.compromisopago else 0,
                                              rubro.refinanciado, rubro.bloqueado, rubro.coactiva)
                                        cursor.execute(sql)

                                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (
                                            rubro.id)
                                        cursor.execute(sql)
                                        registro = cursor.fetchone()
                                        rubroepunemi = registro[0]

                                        rubro.idrubroepunemi = rubroepunemi
                                        rubro.save()
                                    else:
                                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (
                                            rubro.id)
                                        cursor.execute(sql)
                                        rubronoc = cursor.fetchone()
                                        if rubronoc is not None:
                                            sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (
                                            registrorubro[0])
                                            cursor.execute(sql)
                                            tienerubropagos = cursor.fetchone()

                                            if tienerubropagos is not None:
                                                pass
                                            else:
                                                sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                                   valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                                   valortotal = %s, observacion = '%s', tipo_id = %s
                                                   WHERE id=%s; """ % (
                                                    rubro.nombre, rubro.fecha, rubro.fechavence, rubro.saldo,
                                                    rubro.saldo, rubro.iva_id,
                                                    rubro.valoriva, rubro.valor, rubro.valortotal, rubro.observacion,
                                                    tipootrorubro,
                                                    registrorubro[0])
                                                cursor.execute(sql)
                                            rubro.idrubroepunemi = registrorubro[0]
                                            rubro.save()
                            if idioma == 'es':
                                send_html_mail("Confirmación de Registro al Congreso SRRNet",
                                               "emails/xxisrrnet_es.html",
                                               {
                                                   'sistema': 'SGA',
                                                   'persona': datospersona,
                                                   't': miinstitucion(),
                                                   'rubro':rubro,
                                                   'ins':inscripcioncurso,
                                               },
                                               datospersona.lista_emails(), [],
                                               cuenta=CUENTAS_CORREOS[36][1])
                            elif idioma == 'en':
                                send_html_mail("Successful Registration for SRRNet Conference",
                                               "emails/xxisrrnet_en.html",
                                               {
                                                   'sistema': 'SGA',
                                                   'persona': datospersona,
                                                   't': miinstitucion(),
                                                   'rubro':rubro,
                                                   'ins':inscripcioncurso,
                                               },
                                               datospersona.lista_emails(), [],
                                               cuenta=CUENTAS_CORREOS[36][1])
                            return JsonResponse({'result': 'ok',
                                                 "mensaje": u"Estimado participante, Usted se encuentra correctamente inscrito/a." if idioma == 'es' else 'Dear attendee, your registration has been confirmed.',
                                                 "aviso": u"{} se encuentra correctamente inscrito.".format(
                                                     datospersona.nombre_completo()),
                                                 'usuario':usuario_log, 'password':hashed_password_ac})
                        else:
                            raise NameError("No hay datos de persona")
                    else:
                        raise NameError("Lo sentimos el cupo esta completo")
                    res_js = {'result':'ok'}
                except Exception as ex:
                    transaction.set_rollback(True)
                    msg_err = f'{ex}({sys.exc_info()[-1].tb_lineno})'
                    res_js = {'result':'bad', "mensaje":msg_err}
                return JsonResponse(res_js)

            elif action == 'addregistroctt':
                try:
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip()
                    tipoiden = request.POST['id_tipoiden']
                    telefono = request.POST['telefono']
                    tema = request.POST.get('tema', '')
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    email = request.POST['email']
                    sexo = request.POST['genero']
                    pais = int(request.POST['pais'])
                    deseacertifi = json.loads(request.POST['deseacertifi'])
                    id_participaciones = request.POST['id_participaciones']
                    participacion = TipoParticipacionCongreso.objects.get(status=True, id=id_participaciones)
                    nombre_institucion = request.POST['institucion']

                    congreso = Congreso.objects.get(pk=request.POST['cursoid'])
                    existe_unemi = False
                    if congreso.cupo > congreso.inscritocongreso_set.filter(status=True).count():

                        if tipoiden == '1':
                            if Persona.objects.filter(Q(cedula=cedula) |Q(pasaporte=cedula),status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula),
                                                                      status=True)
                                if datospersona.count() > 1:
                                    raise NameError(
                                        u"La cedula ingresada se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")

                                datospersona = datospersona[0]
                                datospersona.email = email
                                datospersona.telefono = telefono
                                datospersona.save(request)
                                existe_unemi=True
                            else:
                                datospersona = Persona(cedula=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       telefono=telefono,
                                                       nacimiento=datetime.now().date(),
                                                       pais_id=pais
                                                       )
                                datospersona.save(request)
                        if tipoiden == '2':
                            if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula), status=True).exists():
                                datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula),status=True)
                                if datospersona.count() > 1:
                                    raise NameError( u"El pasaporte ingresado se encuentra asociado a más de una persona, por favor comunicarse con desarrollo.sistemas@unemi.edu.ec ")
                                datospersona = datospersona[0]
                                datospersona.email = email
                                datospersona.telefono = telefono
                                datospersona.save(request)
                                existe_unemi=True
                            else:
                                datospersona = Persona(pasaporte=cedula,
                                                       nombres=nombres,
                                                       apellido1=apellido1,
                                                       apellido2=apellido2,
                                                       email=email,
                                                       sexo_id=sexo,
                                                       telefono=telefono,
                                                       nacimiento=datetime.now().date(),
                                                       pais_id=pais
                                                       )
                                datospersona.save(request)

                        if datospersona:
                            if not datospersona.externo_set.filter(status=True).exists():
                                datospersonaexterna = Externo(persona=datospersona,
                                                              nombrecomercial='',
                                                              nombrecontacto='',
                                                              )
                                datospersonaexterna.save(request)

                            if not InscritoCongreso.objects.filter(participante=datospersona, congreso=congreso, status=True).exists():
                                inscripcioncurso = InscritoCongreso(participante=datospersona,
                                                                    congreso=congreso,
                                                                    tipoparticipacion=participacion,
                                                                    observacion="Inscrito el %s" % hoy,
                                                                    tema=tema,
                                                                    nombreinstitucion= nombre_institucion,
                                                                    requiere_certificado=deseacertifi
                                                                    )
                                inscripcioncurso.save(request)



                            if inscripcioncurso.requiere_certificado:
                                costo_curso_total = participacion.valor
                                fechamaxpago = date(year=2023, month=12, day=15)
                                tiporubrocongreso = congreso.tiporubro
                                rubro = Rubro(tipo=tiporubrocongreso,
                                              persona=datospersona,
                                              congreso=congreso,
                                              relacionados=None,
                                              nombre=tiporubrocongreso.nombre + ' - ' + congreso.nombre,
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
                                cursor = connections['epunemi'].cursor()
                                sql = """SELECT pe.id,pe.usuario_id FROM sga_persona AS pe WHERE (pe.cedula='%s') AND pe.status=TRUE;  """ % (
                                    datospersona.cedula)
                                cursor.execute(sql)
                                idalumno = cursor.fetchone()
                                usuario_id = 'null'
                                hashed_password = make_password(datospersona.cedula)
                                hashed_password_ac = f'{datospersona.cedula}'
                                usuario_log = f'{datospersona.usuario.username if datospersona.usuario else "N/A"}' if existe_unemi else f'{datospersona.cedula}'
                                if idalumno is None:
                                    if existe_unemi:
                                        usuario_log = f'{datospersona.usuario.username}'
                                        sql = f"""
                                        SELECT us.id FROM auth_user us WHERE username = '{datospersona.usuario.username}';
                                        """
                                        cursor.execute(sql)
                                        usuario = cursor.fetchone()
                                        if usuario is None:
                                            sql = f"""
                                            INSERT INTO auth_user (username, password, email, first_name, last_name, is_active, is_staff, is_superuser)
                                            VALUES ('{datospersona.usuario.username}', '{hashed_password}', '', '', '', TRUE, FALSE, FALSE);
                                            """
                                            cursor.execute(sql)
                                            sql = f"""
                                            SELECT us.id FROM auth_user us WHERE username = '{datospersona.usuario.username}';
                                            """
                                            cursor.execute(sql)
                                            usuario_id = cursor.fetchone()
                                            usuario_id = usuario_id[0]
                                        else:
                                            usuario_id = usuario[0]
                                            sql = f"""
                                            UPDATE auth_user SET password = '{hashed_password}' WHERE id = {usuario_id}
                                            """
                                            cursor.execute(sql)
                                    else:
                                        usuario_log = f'{datospersona.cedula}'
                                        sql = f"""
                                        SELECT us.id FROM auth_user us WHERE username = '{datospersona.cedula}';
                                        """
                                        cursor.execute(sql)
                                        usuario = cursor.fetchone()
                                        if usuario is None:
                                            sql = f"""
                                            INSERT INTO auth_user (username, password, email, first_name, last_name, is_active, is_staff, is_superuser,date_joined)
                                            VALUES ('{datospersona.cedula}', '{hashed_password}', '', '', '', TRUE, FALSE, FALSE, NOW());
                                            """
                                            cursor.execute(sql)
                                            sql = f"""
                                            SELECT us.id FROM auth_user us WHERE username = '{datospersona.cedula}';
                                            """
                                            cursor.execute(sql)
                                            usuario_id = cursor.fetchone()
                                            usuario_id = usuario_id[0]
                                        else:
                                            usuario_id = usuario[0]
                                            sql = f"""
                                            UPDATE auth_user SET password = '{hashed_password}' WHERE id = {usuario_id}
                                            """
                                            cursor.execute(sql)
                                    sql = f""" INSERT INTO sga_persona (status,usuario_id, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                                                            nacimiento, tipopersona, direccion,
                                                                            telefono, email, contribuyenteespecial,
                                                                            anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                                                            regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                                                            tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                                                            acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                                                            idunemi, sector,direccion2,num_direccion,telefono_conv)
                                                                                    VALUES(TRUE,{usuario_id}, '{datospersona.nombres}', '{datospersona.apellido1}', '{datospersona.apellido2}', '{datospersona.cedula}', '{datospersona.ruc}', '{datospersona.pasaporte}', '/{datospersona.nacimiento}/', {datospersona.tipopersona if datospersona.tipopersona else 1}, '{datospersona.direccion}', '{datospersona.telefono}', '{datospersona.email}',
                                                                                    FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE,
                                                                                    FALSE, FALSE, 0, '','','',''); """
                                    cursor.execute(sql)
                                    if datospersona.sexo:
                                        sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (
                                            datospersona.sexo.id)
                                        cursor.execute(sql)
                                        sexo = cursor.fetchone()
                                        if sexo is not None:
                                            sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (
                                            sexo[0], datospersona.cedula)
                                            cursor.execute(sql)
                                    if datospersona.pais:
                                        sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (
                                            datospersona.pais.id)
                                        cursor.execute(sql)
                                        pais = cursor.fetchone()

                                        if pais is not None:
                                            sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (
                                                pais[0], datospersona.cedula)
                                            cursor.execute(sql)
                                    sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (
                                        datospersona.cedula,
                                        datospersona.cedula,
                                        datospersona.cedula)
                                    cursor.execute(sql)
                                    idalumno = cursor.fetchone()
                                    alumnoepu = idalumno[0]
                                else:
                                    alumnoepu = idalumno[0]
                                sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (
                                    rubro.tipo.id)
                                cursor.execute(sql)
                                registro = cursor.fetchone()
                                if registro is not None:
                                    tipootrorubro = registro[0]
                                else:
                                    sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (
                                        rubro.tipo.tiporubro)
                                    cursor.execute(sql)
                                    centrocosto = cursor.fetchone()
                                    idcentrocosto = centrocosto[0]

                                    # Consulto la cuenta contable
                                    cuentacontable = CuentaContable.objects.get(partida=rubro.tipo.partida, status=True)
                                    # Creo el tipo de rubro en epunemi
                                    sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                                                                                               VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                        rubro.tipo.nombre, cuentacontable.partida.id, rubro.tipo.valor,
                                        rubro.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                        rubro.tipo.id)
                                    cursor.execute(sql)

                                    print(".:: Tipo de Rubro creado en EPUNEMI ::.")
                                    # Obtengo el id recién creado del tipo de rubro
                                    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (
                                        rubro.tipo.id)
                                    cursor.execute(sql)
                                    registro = cursor.fetchone()
                                    tipootrorubro = registro[0]
                                # pregunto si no existe rubro con ese id de unemi
                                sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (
                                    rubro.id)
                                cursor.execute(sql)
                                registrorubro = cursor.fetchone()
                                if registrorubro is None:
                                    # Creo nuevo rubro en epunemi
                                    sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                                                                        valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                                                                        idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                                                                        valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                                                                        titularcambiado, coactiva) 
                                                                                      VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                          % (
                                              alumnoepu, rubro.nombre, rubro.cuota, rubro.tipocuota, rubro.fecha,
                                              rubro.fechavence, rubro.saldo,
                                              rubro.saldo, rubro.iva_id, rubro.valoriva, rubro.valor,
                                              rubro.valortotal, rubro.cancelado, rubro.observacion, rubro.id,
                                              tipootrorubro,
                                              rubro.compromisopago if rubro.compromisopago else 0,
                                              rubro.refinanciado, rubro.bloqueado, rubro.coactiva)
                                    cursor.execute(sql)
                                    sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (
                                        rubro.id)
                                    cursor.execute(sql)
                                    registro = cursor.fetchone()
                                    rubroepunemi = registro[0]

                                    rubro.idrubroepunemi = rubroepunemi
                                    rubro.save()
                                else:
                                    sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (
                                        rubro.id)
                                    cursor.execute(sql)
                                    rubronoc = cursor.fetchone()
                                    if rubronoc is not None:
                                        sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (
                                            registrorubro[0])
                                        cursor.execute(sql)
                                        tienerubropagos = cursor.fetchone()

                                        if tienerubropagos is not None:
                                            pass
                                        else:
                                            sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                                                                  valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                                                                  valortotal = %s, observacion = '%s', tipo_id = %s
                                                                                  WHERE id=%s; """ % (
                                                rubro.nombre, rubro.fecha, rubro.fechavence, rubro.saldo,
                                                rubro.saldo, rubro.iva_id,
                                                rubro.valoriva, rubro.valor, rubro.valortotal, rubro.observacion,
                                                tipootrorubro,
                                                registrorubro[0])
                                            cursor.execute(sql)
                                        rubro.idrubroepunemi = registrorubro[0]
                                        rubro.save()
                            return JsonResponse({'result': 'ok', 'certificado': 'si' if inscripcioncurso.requiere_certificado else 'no', "mensaje": u"Estimado participante, Usted se encuentra correctamente inscrito/a.", "aviso": u"{} se encuentra correctamente inscrito.".format(datospersona.nombre_completo())})
                        else:

                            raise NameError("No hay datos de persona")
                            # return JsonResponse({'result': 'si',
                            #                      "mensaje": u"{} ya se encuentra matriculado en el congreso.".format(
                            #                          datospersona.nombre_completo())})
                    else:
                        return JsonResponse({'result': 'bad', "mensaje": u"Lo sentimos el cupo está completo."})



                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad",
                                         "mensaje": f"Error al guardar los datos. {ex}({sys.exc_info()[-1].tb_lineno})"})

            elif action == 'consultacedula':
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
                    nombreinstitucion = ''
                    pais = 0
                    if Persona.objects.filter(cedula=cedula).exists():
                        datospersona = Persona.objects.get(cedula=cedula)
                    if Persona.objects.filter(pasaporte=cedula).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula)
                    if datospersona:
                        if datospersona.sexo:
                            idgenero = datospersona.sexo.id
                        if datospersona.provincia:
                            provinciaid = datospersona.provincia.id
                        if datospersona.pais:
                            pais = datospersona.pais.id
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
                        if datospersona.es_estudiante() or datospersona.es_docente() or datospersona.es_administrativo():
                            nombreinstitucion = 'Universidad Estatal de Milagro'

                        if not InscritoCongreso.objects.filter(participante=datospersona, congreso=codigocurso, status=True).exists():
                            return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                                 "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono,
                                                 "direccion1": datospersona.direccion, "direccion2": datospersona.direccion2,
                                                 "nacimiento": datospersona.nacimiento,"paisid": pais,
                                                 "provinciaid": provinciaid, "cantonid": cantonid, "cantonnom": cantonnom,
                                                 "lugarestudio": lugarestudio,"carrera": carrera,"profesion": profesion,
                                                 "institucionlabora": institucionlabora,"cargo": cargo,"teleoficina": teleoficina,"idgenero": idgenero,"habilitaemail": 1,
                                                 "nombreinstitucion": nombreinstitucion})
                        else:
                            miinscripcion = InscritoCongreso.objects.get(participante=datospersona, congreso=codigocurso, status=True)
                            inscritoconrubro = 'no'
                            if miinscripcion.requiere_certificado:
                                inscritoconrubro = 'si'
                            return JsonResponse({"result": "si", "inscritoconrubro":inscritoconrubro, "mensaje": u"Usted ya se encuentra inscrito en el congreso: </br>" + codigocurso.nombre + ' - ' + miinscripcion.observacion, "aviso": u"{} ya se encuentra inscrito en el congreso: </br>".format(datospersona.nombre_completo()) + codigocurso.nombre + ' - ' + miinscripcion.observacion })
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'consultacedulaxxisrrnet':
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
                    nombreinstitucion = ''
                    pais = 0
                    if Persona.objects.filter(cedula=cedula).exists():
                        datospersona = Persona.objects.get(cedula=cedula)
                    if Persona.objects.filter(pasaporte=cedula).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula)
                    if datospersona:
                        if datospersona.sexo:
                            idgenero = datospersona.sexo.id
                        if datospersona.provincia:
                            provinciaid = datospersona.provincia.id
                        if datospersona.pais:
                            pais = datospersona.pais.id
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
                        if datospersona.es_estudiante() or datospersona.es_profesor() or datospersona.es_administrativo():
                            nombreinstitucion = 'Universidad Estatal de Milagro'

                        if not InscritoCongreso.objects.filter(participante=datospersona, congreso=codigocurso, status=True).exists():
                            return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                                 "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono,
                                                 "direccion1": datospersona.direccion, "direccion2": datospersona.direccion2,
                                                 "nacimiento": datospersona.nacimiento,"paisid": pais,
                                                 "provinciaid": provinciaid, "cantonid": cantonid, "cantonnom": cantonnom,
                                                 "lugarestudio": lugarestudio,"carrera": carrera,"profesion": profesion,
                                                 "institucionlabora": institucionlabora,"cargo": cargo,"teleoficina": teleoficina,"idgenero": idgenero,"habilitaemail": 1,
                                                 "nombreinstitucion": nombreinstitucion})
                        else:
                            idioma = request.POST.get('idioma',None)
                            mensaje_2 = ''
                            if idioma == 'es':
                                mensaje_2 = "Usted ya se encuentra inscrito en el congreso"
                            elif idioma =='en':
                                mensaje_2 = "You're already registered"
                            error_msg = ''
                            usuario_name = ''
                            password = ''
                            miinscripcion = InscritoCongreso.objects.get(participante=datospersona, congreso=codigocurso, status=True)
                            cursor = connections['epunemi'].cursor()
                            sql = f"""
                                SELECT per.id, per.usuario_id FROM sga_persona per WHERE per.cedula='{miinscripcion.participante.cedula}'
                            """
                            cursor.execute(sql)
                            persona_epunemi = cursor.fetchone()
                            if persona_epunemi is None:
                                error_msg = 'An issue occurred while finding your user on the platform https://epunemi.gob.ec/'
                            else:
                                usuario_id = persona_epunemi[1]
                                sql = f"""
                                    SELECT us.username FROM auth_user us WHERE us.id={usuario_id}
                                """
                                cursor.execute(sql)
                                username = cursor.fetchone()
                                if username is None:
                                    error_msg = 'An issue occurred while finding your user on the platform https://epunemi.gob.ec/'
                                else:
                                    usuario_name = f'{username[0]}'
                                    password = f'{datospersona.cedula}'

                            inscritoconrubro = 'no'
                            if miinscripcion.requiere_certificado:
                                inscritoconrubro = 'si'
                            return JsonResponse({"result": "si", "usuario":usuario_name, "password": password, "inscritoconrubro":inscritoconrubro, "mensaje": f"{mensaje_2}: </br>" + codigocurso.nombre + ' - ' + miinscripcion.observacion, "aviso": u"{} ya se encuentra inscrito en el congreso: </br>".format(datospersona.nombre_completo()) + codigocurso.nombre + ' - ' + miinscripcion.observacion })
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
                        lista.append([part.id, part.nombre_completo(), u"%s"%part.valor])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'verificaparticipacionvturismo':
                try:
                    codigocurso = Congreso.objects.get(pk=request.POST['id'])
                    participaciones = TipoParticipacionCongreso.objects.filter(status=True, congreso=codigocurso)
                    lista = []
                    for part in participaciones:
                        lista.append([part.id, u"%s"%part.tipoparticipante, u"%s"%part.valor])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'validarparticipacion':
                try:
                    participacion = request.POST['participacion'].strip()
                    participacion = TipoParticipacionCongreso.objects.get(status=True, id=participacion)
                    if participacion.tipoparticipante_id in [2,4,5,10,11,21,33,34]:
                        cedula = request.POST['cedula'].strip()
                        datospersona = None
                        if Persona.objects.filter(cedula=cedula, status=True).exists():
                            datospersona = Persona.objects.get(cedula=cedula, status=True)
                        elif Persona.objects.filter(pasaporte=cedula, status=True).exists():
                            datospersona = Persona.objects.get(pasaporte=cedula, status=True)
                        if not datospersona:
                            return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como usuario de UNEMI", "aviso": "No consta como usuario de UNEMI" })
                        else:
                            # DOCENTES
                            if participacion.tipoparticipante_id in [4,10]:
                                if not datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True, regimenlaboral__id=2).exists():
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como docente de UNEMI", "aviso": "No consta como docente de UNEMI"})
                            elif participacion.tipoparticipante_id in [21]:
                                if not datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True,
                                                                                   regimenlaboral__id=1).exists():
                                    return JsonResponse(
                                        {"result": "bad", "costocurso": "Ud, no consta como administrativo de UNEMI",
                                         "aviso": "No consta como administrativo de UNEMI"})

                            elif participacion.tipoparticipante_id in [2,11]:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    if not Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True, cerrada=False).exists():
                                            return JsonResponse({"result": "bad", "costocurso": "Ud, no consta con una matrícula activa en UNEMI", "aviso": "No consta con una matrícula activa en UNEMI"})
                                else:
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta con una matrícula activa en UNEMI", "aviso": "No consta con una matrícula activa en UNEMI"})
                            elif participacion.tipoparticipante_id == 5:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    if not Graduado.objects.filter(inscripcion__id__in=verificainsripcion, status=True).exists():
                                        return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI", "aviso": "No consta como graduado de UNEMI"})
                                else:
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI", "aviso": "No consta como graduado de UNEMI"})
                            elif participacion.tipoparticipante_id in [33,34]:
                                estudiante_pregrado = datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists()
                                docente_unemi_pregrado = datospersona.distributivopersona_set.filter(estadopuesto_id=1, status=True, regimenlaboral__id=2).exists()
                                if estudiante_pregrado:
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    matricula_activda = Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True, cerrada=False).exists()
                                    if docente_unemi_pregrado:
                                        pass
                                    elif matricula_activda:
                                        pass
                                    else:
                                        return JsonResponse({"result": "bad",
                                                                 "costocurso": "Ud, no consta como docente/estudiante de UNEMI",
                                                                 "aviso": "No consta como docente/estudiante de UNEMI"})
                                elif not docente_unemi_pregrado:
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como docente/estudiante de UNEMI", "aviso": "No consta como docente/estudiante de UNEMI"})
                                else:
                                    pass

                    return JsonResponse({"result": "ok", "costocurso": participacion.valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'validarparticipacion_v2':
                try:
                    participacion = request.POST['participacion'].strip()
                    participacion = TipoParticipacionCongreso.objects.get(status=True, id=participacion)
                    if participacion.tipoparticipante_id in [2,4,5,10,11]:
                        cedula = request.POST['cedula'].strip()
                        datospersona = None
                        if Persona.objects.filter(cedula=cedula, status=True).exists():
                            datospersona = Persona.objects.get(cedula=cedula, status=True)
                        elif Persona.objects.filter(pasaporte=cedula, status=True).exists():
                            datospersona = Persona.objects.get(pasaporte=cedula, status=True)
                        if not datospersona:
                                return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como usuario de UNEMI", "aviso": "No consta como usuario de UNEMI" })
                        else:
                            # DOCENTES
                            if participacion.tipoparticipante_id in [4,10]:
                                if not datospersona.profesor_set.filter(status=True, activo=True).exists():
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como docente de UNEMI", "aviso": "No consta como docente de UNEMI"})
                            elif participacion.tipoparticipante_id in [2,11]:
                                if not datospersona.inscripcion_set.filter(status=True, activo=True).exclude(coordinacion_id=9).exists():
                                    # verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    # if not Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True, cerrada=False).exists():
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como estudiante activo en UNEMI", "aviso": "No consta como estudiante activo en UNEMI"})
                                # else:
                                #     return JsonResponse({"result": "bad", "costocurso": "Ud, no consta con una matrícula activa en UNEMI", "aviso": "No consta con una matrícula activa en UNEMI"})
                            elif participacion.tipoparticipante_id == 5:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    if not Graduado.objects.filter(inscripcion__id__in=verificainsripcion, status=True).exists():
                                        return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI", "aviso": "No consta como graduado de UNEMI"})
                                else:
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI", "aviso": "No consta como graduado de UNEMI"})
                    return JsonResponse({"result": "ok", "costocurso": participacion.valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'validarparticipacion_v3':
                try:
                    participacion = request.POST['participacion'].strip()
                    participacion = TipoParticipacionCongreso.objects.get(status=True, id=participacion)
                    if participacion.tipoparticipante_id in [2,4,5,10,11,18,19,20,33]:
                        cedula = request.POST['cedula'].strip()
                        datospersona = None
                        if Persona.objects.filter(cedula=cedula, status=True).exists():
                            datospersona = Persona.objects.get(cedula=cedula, status=True)
                        elif Persona.objects.filter(pasaporte=cedula, status=True).exists():
                            datospersona = Persona.objects.get(pasaporte=cedula, status=True)

                        if not datospersona and participacion.tipoparticipante_id in [2,11,4,10,5]:
                                return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como usuario de UNEMI", "aviso": "No consta como usuario de UNEMI" })
                        elif datospersona:
                            if participacion.tipoparticipante_id == 18:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(
                                        status=True).exclude(coordinacion_id=9)
                                    if Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True,
                                                                cerrada=False).exists():
                                        return JsonResponse({"result": "bad",
                                                             "costocurso": "Ud, consta como estudiante activo en UNEMI, seleccione la opción correcta.",
                                                             "aviso": "Consta como estudiante activo en UNEMI , seleccione la opción correcta."})

                            # DOCENTES
                            if participacion.tipoparticipante_id in [4,10]:
                                if not datospersona.profesor_set.filter(status=True, activo=True).exists():
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como docente de UNEMI", "aviso": "No consta como docente de UNEMI"})
                            elif participacion.tipoparticipante_id in [2,11]:
                                if not datospersona.inscripcion_set.filter(status=True, activo=True).exclude(coordinacion_id=9).exists():
                                    # verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    # if not Matricula.objects.filter(inscripcion__id__in=verificainsripcion, status=True, cerrada=False).exists():
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como estudiante activo en UNEMI", "aviso": "No consta como estudiante activo en UNEMI"})

                            elif participacion.tipoparticipante_id == 5:
                                if datospersona.inscripcion_set.filter(status=True).exclude(coordinacion_id=9).exists():
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(status=True).exclude(coordinacion_id=9)
                                    if not Graduado.objects.filter(inscripcion__id__in=verificainsripcion, status=True).exists():
                                        return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI", "aviso": "No consta como graduado de UNEMI"})
                                else:
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como graduado de UNEMI", "aviso": "No consta como graduado de UNEMI"})

                            elif participacion.tipoparticipante_id == 19:
                                if not datospersona.ppl:
                                    return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como estudiante PPL", "aviso": "No consta como estudiante PPL"})

                            elif participacion.tipoparticipante_id == 20:
                                    verificainsripcion = datospersona.inscripcion_set.values_list('id').filter(
                                        status=True).exclude(coordinacion_id=9)
                                    if not Matricula.objects.filter(inscripcion__id__in=verificainsripcion, inscripcion__persona__perfilinscripcion__verificadiscapacidad=True ,status=True,
                                                                cerrada=False).exists():
                                        return JsonResponse({"result": "bad", "costocurso": "Ud, no consta como estudiante con discapacidad",
                                                             "aviso": "No consta como estudiante con discapacidad"})

                                # if datospersona.profesor_set.filter(status=True, activo=True).exists():
                                #     return JsonResponse({"result": "bad", "costocurso": "Ud, discapacidad", "aviso": "No consta como docente de UNEMI"})


                    return JsonResponse({"result": "ok", "costocurso": participacion.valor})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'inscripciongeneral':
                try:
                    hoy = datetime.now().date()
                    cursos = None
                    listacur = []
                    if Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , visualizar=True, status=True).exclude(id__in=[5,8,9,7]).exists():
                        cursos = Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, visualizar=True, status=True).exclude(id__in=[5,8,9,7])
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
                    data['currenttime'] = datetime.now()
                    return render(request, "inscripcionescongresos/inscripcionescongresos.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscripcionsalud':
                try:
                    hoy = datetime.now().date()
                    cursos = None
                    listacur = []
                    if Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , visualizar=True, status=True,id__in=[5,8,9,7]).exists():
                        cursos = Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, visualizar=True, status=True,id__in=[5,8,9,7])
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
                    data['currenttime'] = datetime.now()
                    return render(request, "inscripcionescongresos/inscripcionescongresossalud.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscripcionadministrativas':
                try:
                    hoy = datetime.now().date()
                    cursos = None
                    listacur = []
                    if Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , visualizar=True, status=True).exclude(id__in=[5,8,9,7,18]).exists():
                        cursos = Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, visualizar=True, status=True).exclude(id__in=[5,8,9,7,18])
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
                    data['currenttime'] = datetime.now()
                    return render(request, "inscripcionescongresos/inscripcionadministrativas.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscripcionturismo':
                try:
                    hoy = datetime.now().date()
                    cursos = None
                    listacur = []
                    if Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy , visualizar=True, status=True, id=18 ).exists():
                        cursos = Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, visualizar=True, status=True, id=18)
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
                    data['currenttime'] = datetime.now()
                    return render(request, "inscripcionescongresos/inscripcionturismo.html", data)
                except Exception as ex:
                    pass

            elif action == 'xxisrrnetregistration_enx':
                try:
                    id_tipoparticipante_en = variable_valor('TIPO_PARTICIPANTE_EN')
                    hoy = datetime.now().date()
                    cursos = None
                    id = 21
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET.get('id',None)))
                    form = CongresoXXISRRNetFormEN()

                    listacur = []
                    if Congreso.objects.values('id').filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, visualizar=True, status=True).exclude(id__in=[5, 8, 9, 7]).exists():
                        cursos = Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy,
                                                         visualizar=True, status=True).exclude(id__in=[5, 8, 9, 7])
                        for cur in cursos:
                            if cur.cupo > cur.inscritocongreso_set.filter(status=True).count():
                                listacur.append(cur.id)
                        if listacur:
                            cursos = Congreso.objects.filter(pk__in=listacur)
                        else:
                            cursos = None
                        if not TipoOtroRubro.objects.filter(
                                pk__in=cursos.values_list('tiporubro_id').filter(status=True)).exists():
                            cursos = None
                        form.fields['congreso'].queryset = cursos
                    form.fields['tipoparticipante'].queryset = TipoParticipacionCongreso.objects.none()
                    if id:
                        congreso = Congreso.objects.filter(status=True,id=id)
                        form.fields['congreso'].initial = congreso.first()
                        form.fields['congreso'].queryset = congreso
                        form.fields['tipoparticipante'].queryset = TipoParticipacionCongreso.objects.filter(status=True, congreso=congreso.first(), id__in=id_tipoparticipante_en)
                    data['title'] = 'Registration'
                    data['form'] = form
                    return render(request, 'inscripcionescongresos/xxisrrnet/viewregistration_en.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(f'/inscripcionescongresos?action=inscripciongeneral&info={ex} ({sys.exc_info()[-1].tb_lineno})')

            elif action == 'xxisrrnetinsrcipcion_es':
                try:
                    id_tipoparticipante_en = variable_valor('TIPO_PARTICIPANTE_ES')
                    hoy = datetime.now().date()
                    cursos = None
                    id = 21
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET.get('id',None)))
                    form = CongresoXXISRRNetFormES()

                    listacur = []
                    if Congreso.objects.values('id').filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy, visualizar=True, status=True).exclude(id__in=[5, 8, 9, 7]).exists():
                        cursos = Congreso.objects.filter(fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy,
                                                         visualizar=True, status=True).exclude(id__in=[5, 8, 9, 7])
                        for cur in cursos:
                            if cur.cupo > cur.inscritocongreso_set.filter(status=True).count():
                                listacur.append(cur.id)
                        if listacur:
                            cursos = Congreso.objects.filter(pk__in=listacur)
                        else:
                            cursos = None
                        if not TipoOtroRubro.objects.filter(
                                pk__in=cursos.values_list('tiporubro_id').filter(status=True)).exists():
                            cursos = None
                        form.fields['congreso'].queryset = cursos
                    form.fields['tipoparticipante'].queryset = TipoParticipacionCongreso.objects.none()
                    if id:
                        congreso = Congreso.objects.filter(status=True,id=id)
                        form.fields['congreso'].initial = congreso.first()
                        form.fields['congreso'].queryset = congreso
                        form.fields['tipoparticipante'].queryset = TipoParticipacionCongreso.objects.filter(status=True, congreso=congreso.first(), id__in=id_tipoparticipante_en)
                    data['title'] = 'Inscripción al Congreso'
                    form.fields['provincia'].queryset = Provincia.objects.none()
                    data['form'] = form
                    return render(request, 'inscripcionescongresos/xxisrrnet/viewinscripcion.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(f'/inscripcionescongresos?action=inscripciongeneral&info={ex} ({sys.exc_info()[-1].tb_lineno})')

            elif action == 'congtendturisticas':
                try:
                    hoy = datetime.now().date()
                    cursos = None
                    id = 20
                    if 'id' in request.GET:
                        id = int(encrypt(request.GET.get('id', None)))
                    form = InscripTuristicoForm()
                    if id:
                        congreso = Congreso.objects.filter(status=True,id=20)
                        form.fields['congreso'].initial = congreso.first()
                        form.fields['congreso'].queryset = congreso
                        form.fields['tipoparticipante'].queryset = TipoParticipacionCongreso.objects.filter(status=True, congreso=congreso.first())
                    data['title'] = 'Registro'
                    data['form'] = form
                    return render(request, 'inscripcionescongresos/ctendenciaturistica/viewinscripcionctt.html', data)


                except Exception as ex:
                    return HttpResponseRedirect(f'/inscripcionescongresos?action=inscripciongeneral&info={ex} ({sys.exc_info()[-1].tb_lineno})')

            elif action == 'viewinternational_transfer':
                try:
                    data['title'] = u'International Transfer'
                    return render(request, 'inscripcionescongresos/xxisrrnet/viewinternational_transfer.html', data)
                except Exception as ex:
                    pass



            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'
                hoy = datetime.now().date()
                cursos = None
                return HttpResponseRedirect("/inscripcionescongresos?action=inscripcion")
                # return render(request, "inscripcionescongresos/inscripcionescongresos.html", data)
            except Exception as ex:
                pass
