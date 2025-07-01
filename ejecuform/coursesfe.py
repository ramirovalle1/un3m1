from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from decorators import last_access, secure_module
from django.db import transaction
from sga.commonviews import adduserdata
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from .models import InscripcionInteresadoFormacionEjecutiva, CategoriaEventoFormacionEjecutiva, \
    EventoFormacionEjecutiva, CarritoItem, Carrito, InscripcionFormacionEjecutiva
from sagest.models import Rubro, CuentaContable, Pago
from sga.funciones import MiPaginador, log
from django.db.models import Q
from django.db import transaction, connections
from sga.models import Persona
from api.helpers.response_herlper import Helper_Response
from sga.templatetags.sga_extras import encrypt
from hashlib import md5
from bd.models import UserToken
from settings import SIMPLE_JWT
from rest_framework import status
@login_required(redirect_field_name='ret', login_url='/loginformacionejecutiva')
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['eInteresado'] = eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True, persona=persona)

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'updateitems':
            try:
                nombre = download = costo = id = ide = mes = dia = anio = tiempo = None
                eEvento = EventoFormacionEjecutiva.objects.get(status=True, pk=int(request.POST['ide']))

                if not eEvento.disponible():
                    return JsonResponse({'result': 'bad', 'mensaje':'Lo sentimos, el evento ha finalizado, no puede añadirlo al carrito de compras'})

                est = int(request.POST['est'])
                if not Carrito.objects.filter(status=True, estado=1, interesado=eInteresado).exists():
                    eCarrito = Carrito(interesado=eInteresado)
                    eCarrito.save()
                    log(u'Creó carrito de compra: %s' % eCarrito, request, "add")
                else:
                    eCarrito = Carrito.objects.filter(status=True, estado=1, interesado=eInteresado).first()

                if not CarritoItem.objects.filter(carrito=eCarrito, evento=eEvento).exists():
                    eItem = CarritoItem(carrito=eCarrito, evento=eEvento, fecha=datetime.now())
                    eItem.save()
                    log(u'Añadió item al carrito de compra: %s' % eCarrito, request, "add")
                else:
                    eItem = CarritoItem.objects.filter(carrito=eCarrito, evento=eEvento).first()
                    eItem.fecha = datetime.now()
                    eItem.save()

                id = eItem.id
                ide = eItem.evento.id
                nombre = eItem.evento.nombre
                download = eItem.evento.download_banner()
                costo = eItem.evento.costo_curso_actual()
                mes = nombre_mes(eItem.fecha_creacion.month)
                dia = eItem.fecha_creacion.day
                anio = eItem.fecha_creacion.year

                # Formatear la fecha y convertir a minúsculas
                tiempo = eItem.fecha_creacion.strftime('%I:%M %p').lower()

                if est == 0:
                    eItem.status = True
                else:
                    eItem.status = False
                eItem.save()

                return JsonResponse({'result': 'ok', 'valor': eInteresado.cantidad_elementos(),
                                     'id': id, 'nombre': nombre, 'download_banner': download,
                                     'costo_curso_actual': costo, 'ide':ide, 'mes':mes,
                                     'dia': dia, 'anio':anio, 'tiempo': tiempo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'quitaritems':
            try:
                eItem = CarritoItem.objects.get(pk=int(request.POST['ide']))
                eItem.status = False
                eItem.save()
                return JsonResponse({'result': 'ok', 'valor': f'{eItem.carrito.total_pagar()} US$', 'canti': f'{eItem.carrito.items_cant()} eventos añadidos al carrito', 'cvnt': eItem.carrito.items_cant()})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'generarubros':
            try:
                eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True, persona=persona)
                eCarrito = eInteresado.carrito_actual()

                for eItem in eCarrito.items_carrito():
                    eConvocatoria = eItem.evento.convocatoria_actual()
                    if not InscripcionFormacionEjecutiva.objects.filter(status=True, interesado=eInteresado, convocatoria=eConvocatoria).exists():
                        eInscripcion = InscripcionFormacionEjecutiva(interesado=eInteresado, convocatoria=eConvocatoria)
                        eInscripcion.save()
                    else:
                        eInscripcion = InscripcionFormacionEjecutiva.objects.filter(status=True, interesado=eInteresado, convocatoria=eConvocatoria).first()

                    if not Rubro.objects.filter(status=True, tipo=eConvocatoria.tiporubro, inscritoejecutivo=eInscripcion, persona=eInteresado.persona).exists():
                        fecha_vence = datetime.now().date() + timedelta(days=3)
                        eRubro = Rubro(tipo=eConvocatoria.tiporubro,
                                       persona_id=eInteresado.persona.id,
                                       nombre=f'{eConvocatoria.tiporubro.nombre}'[:299],
                                       cuota=1,
                                       tipocuota=2,
                                       fecha=datetime.now().date(),
                                       fechavence=fecha_vence,
                                       valor=eConvocatoria.costo,
                                       iva_id=1,
                                       valoriva=0,
                                       valortotal=eConvocatoria.costo,
                                       saldo=eConvocatoria.costo,
                                       cancelado=False,
                                       inscritoejecutivo=eInscripcion)
                        eRubro.save(request)

                        # -------CREAR PERSONA EPUNEMI-------
                        cursor = connections['epunemi'].cursor()
                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (
                        eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                        cursor.execute(sql)
                        idalumno = cursor.fetchone()

                        if idalumno is None:
                            sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                        nacimiento, tipopersona, sector, direccion,  direccion2,
                                        num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                        anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                        regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                        tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                        acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                        idunemi)
                                                VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s',
                                                FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE,
                                                FALSE, FALSE, 0); """ % (
                                eRubro.persona.nombres, eRubro.persona.apellido1,
                                eRubro.persona.apellido2, eRubro.persona.cedula,
                                eRubro.persona.ruc if eRubro.persona.ruc else '',
                                eRubro.persona.pasaporte if eRubro.persona.pasaporte else '',
                                eRubro.persona.nacimiento,
                                eRubro.persona.tipopersona if eRubro.persona.tipopersona else 1,
                                eRubro.persona.sector if eRubro.persona.sector else '',
                                eRubro.persona.direccion if eRubro.persona.direccion else '',
                                eRubro.persona.direccion2 if eRubro.persona.direccion2 else '',
                                eRubro.persona.num_direccion if eRubro.persona.num_direccion else '',
                                eRubro.persona.telefono if eRubro.persona.telefono else '',
                                eRubro.persona.telefono_conv if eRubro.persona.telefono_conv else '',
                                eRubro.persona.email if eRubro.persona.email else '')
                            cursor.execute(sql)

                            if eRubro.persona.sexo:
                                sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (
                                    eRubro.persona.sexo.id)
                                cursor.execute(sql)
                                sexo = cursor.fetchone()

                                if sexo is not None:
                                    sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (
                                    sexo[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.pais:
                                sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (
                                    eRubro.persona.pais.id)
                                cursor.execute(sql)
                                pais = cursor.fetchone()

                                if pais is not None:
                                    sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (
                                    pais[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.parroquia:
                                sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (
                                    eRubro.persona.parroquia.id)
                                cursor.execute(sql)
                                parroquia = cursor.fetchone()

                                if parroquia is not None:
                                    sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (
                                    parroquia[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.canton:
                                sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (
                                    eRubro.persona.canton.id)
                                cursor.execute(sql)
                                canton = cursor.fetchone()

                                if canton is not None:
                                    sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (
                                    canton[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.provincia:
                                sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (
                                    eRubro.persona.provincia.id)
                                cursor.execute(sql)
                                provincia = cursor.fetchone()

                                if provincia is not None:
                                    sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (
                                    provincia[0], eRubro.persona.cedula)
                                    cursor.execute(sql)
                            # ID DE PERSONA EN EPUNEMI
                            sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (
                            eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                            cursor.execute(sql)
                            idalumno = cursor.fetchone()
                            alumnoepu = idalumno[0]
                        else:
                            alumnoepu = idalumno[0]

                        # Consulto el tipo otro rubro en epunemi
                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                        cursor.execute(sql)
                        registro = cursor.fetchone()

                        # Si existe
                        if registro is not None:
                            tipootrorubro = registro[0]
                        else:
                            # Debo crear ese tipo de rubro
                            # Consulto centro de costo
                            sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (
                                eRubro.tipo.tiporubro)
                            cursor.execute(sql)
                            centrocosto = cursor.fetchone()
                            idcentrocosto = centrocosto[0]

                            # Consulto la cuenta contable
                            cuentacontable = CuentaContable.objects.get(partida=eRubro.tipo.partida, status=True)

                            # Creo el tipo de rubro en epunemi
                            sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                eRubro.tipo.nombre, cuentacontable.partida.id, eRubro.tipo.valor,
                                eRubro.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                eRubro.tipo.id)
                            cursor.execute(sql)

                            print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                            # Obtengo el id recién creado del tipo de rubro
                            sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()
                            tipootrorubro = registro[0]

                        # pregunto si no existe rubro con ese id de unemi
                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (eRubro.id)
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
                                  % (alumnoepu, eRubro.nombre, eRubro.cuota, eRubro.tipocuota, eRubro.fecha, eRubro.fechavence,
                                     eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                     eRubro.valoriva, eRubro.valor,
                                     eRubro.valortotal, eRubro.cancelado, eRubro.observacion, eRubro.id, tipootrorubro,
                                     eRubro.compromisopago if eRubro.compromisopago else 0,
                                     eRubro.refinanciado, eRubro.bloqueado, eRubro.coactiva)
                            cursor.execute(sql)

                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (
                                eRubro.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()
                            rubroepunemi = registro[0]

                            eRubro.idrubroepunemi = rubroepunemi
                            eRubro.epunemi = True
                            eRubro.save()

                            print(".:: Rubro creado en EPUNEMI ::.")
                        else:
                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (
                                eRubro.id)
                            cursor.execute(sql)
                            rubronoc = cursor.fetchone()

                            if rubronoc is not None:
                                sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                cursor.execute(sql)
                                tienerubropagos = cursor.fetchone()

                                if tienerubropagos is not None:
                                    pass
                                else:
                                    sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                       valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                       valortotal = %s, observacion = '%s', tipo_id = %s
                                       WHERE id=%s; """ % (
                                    eRubro.nombre, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                    eRubro.valoriva, eRubro.valor, eRubro.valortotal, eRubro.observacion, tipootrorubro,
                                    registrorubro[0])
                                    cursor.execute(sql)
                                eRubro.idrubroepunemi = registrorubro[0]
                                eRubro.save()

                eCarrito.estado = 2
                eCarrito.save()
                log(u'Generó rubros del inscrito: %s' % eInteresado, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pagarrubros':
            try:
                ePersona = Persona.objects.get(pk=int(request.POST['idp']))
                fecha = datetime.now().date()
                hora = datetime.now().time()
                fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
                token_ = md5(str(encrypt(ePersona.usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
                lifetime = SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
                perfil_ = UserToken.objects.create(user=request.user, token=token_, action_type=5, app=5, isActive=True,
                                                   date_expires=datetime.now() + lifetime)
                # return Helper_Response(isSuccess=True, redirect=', module_access=False, token=True, status=status.HTTP_200_OK)
                return JsonResponse({"result": "ok", "url": f'http://epunemi.gob.ec/oauth2/?tknbtn={token_}&tkn={encrypt(ePersona.id)}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'allevents':
                try:
                    data['title'] = u'Todos los eventos'
                    filtros = Q(status=True, activo=True)

                    url_vars = '&action=allevents'

                    eEventos = EventoFormacionEjecutiva.objects.filter(filtros)
                    paging = MiPaginador(eEventos, 6)
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
                    data['eEventos'] = page.object_list
                    data['url_vars'] = url_vars
                    data['eCategorias'] = CategoriaEventoFormacionEjecutiva.objects.filter(status=True)
                    data['eInteresado'] = eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True,
                                                                                                            persona=persona)
                    data['eCarrito'] = eInteresado.carrito_actual()
                    return render(request, "coursesfe/allevents.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewevent':
                try:
                    # data = {"title": u"Todos los eventos", "background": 9}
                    data['title'] = "Evento"
                    data['eInteresado'] = eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True,
                                                                                                            persona=persona)
                    data['eEvento'] = EventoFormacionEjecutiva.objects.get(status=True, activo=True, pk=int(request.GET['id']))
                    data['eEventos'] = EventoFormacionEjecutiva.objects.filter(status=True, activo=True)
                    data['eCarrito'] = eInteresado.carrito_actual()
                    return render(request, "viewevent.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewcart':
                try:
                    data['title'] = "Carrito de compra"
                    data['eInteresado'] = eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True, persona=persona)
                    data['eCarrito'] = eInteresado.carrito_actual()
                    return render(request, "carrito.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewsuscriptions':
                try:
                    data['title'] = "Mis suscripciones"
                    data['eInteresado'] = eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True, persona=persona)
                    data['eInscripciones'] = eInscripciones = InscripcionFormacionEjecutiva.objects.filter(status=True, interesado=eInteresado)
                    # if eInscripciones:
                    data['eRubros'] = eRubros = Rubro.objects.filter(status=True, persona=persona, inscritoejecutivo__id__in=eInscripciones)
                    # else:
                    #     data['eRubros'] = None
                    return render(request, "missuscripciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewfacturas':
                try:
                    data['title'] = "Mis facturas"
                    data['eInteresado'] = eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True, persona=persona)
                    data['eInscripciones'] = eInscripciones = InscripcionFormacionEjecutiva.objects.filter(status=True, interesado=eInteresado)
                    if eInscripciones:
                        data['eRubros'] = eRubros = Rubro.objects.filter(status=True, persona=persona, inscritoejecutivo__id__in=eInscripciones)
                        data['ePagos'] = ePagos = Pago.objects.filter(status=True, rubro__id__in=eRubros.values_list('id', flat=True))
                    else:
                        data['eRubros'] = None
                    return render(request, "viewfacturas.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewcourses':
                try:
                    data['title'] = "Mis facturas"
                    data['eInteresado'] = eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True, persona=persona)
                    data['eInscripciones'] = eInscripciones = InscripcionFormacionEjecutiva.objects.filter(status=True, interesado=eInteresado)
                    return render(request, "viewcourses.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Gestión de categorías de servicios'
                data['eCategorias'] = CategoriaEventoFormacionEjecutiva.objects.filter(status=True)
                data['eEventosCant'] = EventoFormacionEjecutiva.objects.filter(status=True).count()
                data['eEventos'] = EventoFormacionEjecutiva.objects.filter(status=True, activo=True)
                data['eInteresado'] = eInteresado = InscripcionInteresadoFormacionEjecutiva.objects.get(status=True,
                                                                                                        persona=persona)
                data['eCarrito'] = eInteresado.carrito_actual()
                return render(request, "coursesfe/view.html", data)
            except Exception as ex:
                HttpResponseRedirect(f"/?info={ex.__str__()}")


def nombre_mes(numero):
    meses = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre"
    }

    return meses.get(numero, "Número de mes inválido")