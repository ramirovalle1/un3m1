import threading
from sga.models import *
from sga.funciones_templatepdf import actagradoposgradocomplexivoconintegantesfirmamasivo

class generar_actas_de_grado_masivo(threading.Thread):
    def __init__(self, request):
        self.request = request
        self.persona = request.session.get('persona')
        self.configuracion_id = request.POST.get('id')
        threading.Thread.__init__(self)

    def run(self):
        try:
            print("start process generar_actas_de_grado_masivo")
            actasgeneradas, eroractas, integrantedebefirmar = actagradoposgradocomplexivoconintegantesfirmamasivo(self.request)
            titulonotificacion = f"ACTAS DE GRADO GENERADAS EN MASIVO"
            if eroractas > 0:
                cuerponotificacion = f"Se han generado {actasgeneradas} actas de grado correctamente, y no pudieron ser generadas {eroractas} actas de grado."
            else:
                cuerponotificacion = f"Se han generado {actasgeneradas} actas de grado correctamente."

            if DEBUG:
                url = f"http://127.0.0.1:8000/adm_configuracionpropuesta?action=graduarExamenComplexivo&idconfiguracion={self.configuracion_id }"
            else:
                url = f"https://sga.unemi.edu.ec/adm_configuracionpropuesta?action=graduarExamenComplexivo&idconfiguracion={self.configuracion_id }"

            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=self.persona,
                url=url,
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save(self.request)

            if actasgeneradas > 0:
                titulonotificacion = f"ACTAS DE GRADO PENDIENTES DE FIRMAR"
                cuerponotificacion = f"Se han generado {actasgeneradas} actas de grado, favor revisar y firmar los documentos."
                url = f"https://sga.unemi.edu.ec/firmardocumentosposgrado?action=firmaactagrado"

                if variable_valor("FIRMAR_ACTAS_EN_ORDEN"):
                    notificacion = Notificacion(
                        titulo=titulonotificacion,
                        cuerpo=cuerponotificacion,
                        destinatario=integrantedebefirmar,
                        url=url,
                        content_type=None,
                        object_id=None,
                        prioridad=1,
                        app_label='SGA',
                        fecha_hora_visible=datetime.now() + timedelta(days=3))
                    notificacion.save(self.request)
                else:
                    eTemaTitulacionPosgradoMatriculaId = TemaTitulacionPosgradoMatricula.objects.values_list('id',flat=True).filter(califico=True,actacerrada=True,status=True, estado_acta_firma=4,mecanismotitulacionposgrado__in=(15, 21), convocatoria_id=self.configuracion_id,archivo_acta_grado__isnull=False)
                    eIntegranteFirmaTemaTitulacionPosgradoMatriculaPersona = IntegranteFirmaTemaTitulacionPosgradoMatricula.objects.filter(status=True,tematitulacionposmat_id__in =eTemaTitulacionPosgradoMatriculaId,firmo = False).distinct().values_list('persona',flat=True).order_by('persona')
                    ePersonas = Persona.objects.filter(status=True,pk__in=eIntegranteFirmaTemaTitulacionPosgradoMatriculaPersona)
                    for integrante in ePersonas:
                        notificacion = Notificacion(
                            titulo=titulonotificacion,
                            cuerpo=cuerponotificacion,
                            destinatario=integrante,
                            url=url,
                            content_type=None,
                            object_id=None,
                            prioridad=1,
                            app_label='SGA',
                            fecha_hora_visible=datetime.now() + timedelta(days=3))
                        notificacion.save(self.request)

            print("End proccess generar_actas_de_grado_masivo")
        except Exception as ex:
            pass

class notificar_persona_a_fimar_acta_sustentacion_nota(threading.Thread):
    def     __init__(self, request, eTemaTitulacionPosgradoMatricula):
        self.request = request
        self.eTemaTitulacionPosgradoMatricula = eTemaTitulacionPosgradoMatricula
        threading.Thread.__init__(self)

    def run(self):
        try:
            ACTA_SUSTENTACION_CON_NOTA = 10
            print("start process notification firma acta de sustentacion")
            request, eTemaTitulacionPosgradoMatricula = self.request, self.eTemaTitulacionPosgradoMatricula
            eIntegranteFirmaTemaTitulacionPosgradoMatricula = eTemaTitulacionPosgradoMatricula.get_integrante_firman_por_tipo_acta(ACTA_SUSTENTACION_CON_NOTA)
            titulonotificacion = f"FIRMAR ACTA DE SUSTENTACIÓN: {eTemaTitulacionPosgradoMatricula.matricula.inscripcion}"
            cuerponotificacion = f"Acta de sustentación listo para legalizar, favor firmar el acta por medio del SGA."

            for integrante in eIntegranteFirmaTemaTitulacionPosgradoMatricula:
                ePersona = integrante.persona
                if ePersona:
                    puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden_por_tipo(ePersona,ACTA_SUSTENTACION_CON_NOTA)
                    if puede:
                        if not integrante.firmo:
                            if integrante.ordenfirma_id == 10:
                                ePerfilUsuario = PerfilUsuario.objects.filter(status=True, persona =ePersona, inscripcion =eTemaTitulacionPosgradoMatricula.matricula.inscripcion)
                                if ePerfilUsuario.exists():
                                    cuerponotificacion = f"Acta de sustentación de titulación generada, favor firmar el acta por medio del sistema en la sección de sustentación."

                                    url = f"/alu_tematitulacionposgrado"


                                    notificacion = Notificacion(
                                        titulo=titulonotificacion,
                                        cuerpo=cuerponotificacion,
                                        destinatario=ePersona,
                                        url=url,
                                        content_type=None,
                                        object_id=None,
                                        prioridad=1,
                                        perfil=ePerfilUsuario.first(),
                                        app_label='SIE',
                                        fecha_hora_visible=datetime.now() + timedelta(days=3))
                                    notificacion.save(request)
                            else:
                                if DEBUG:
                                    url = f"http://127.0.0.1:8000/pro_tutoriaposgrado?action=firmardocumentostitulacionposgrado&tipo=actasustentacion&pk={eTemaTitulacionPosgradoMatricula.pk}"
                                else:
                                    url = f"https://sga.unemi.edu.ec/pro_tutoriaposgrado?action=firmardocumentostitulacionposgrado&tipo=actasustentacion&pk={eTemaTitulacionPosgradoMatricula.pk}"

                                notificacion = Notificacion(
                                    titulo=titulonotificacion,
                                    cuerpo=cuerponotificacion,
                                    destinatario=ePersona,
                                    url=url,
                                    content_type=None,
                                    object_id=None,
                                    prioridad=1,
                                    app_label='SGA',
                                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                                notificacion.save(request)
                            break

            if not eIntegranteFirmaTemaTitulacionPosgradoMatricula.filter(firmo=False):
                ids_notificar = variable_valor('ID_PERSONA_NOTIFICAR_ACTAS_FIRMADAS')
                ePersonasNotificar = Persona.objects.filter(status=True,pk__in=ids_notificar)
                if DEBUG:
                    url_revision = f'http://127.0.0.1:8000/adm_configuracionpropuesta?action=tribunaltemas&idconfiguracion={eTemaTitulacionPosgradoMatricula.convocatoria_id}'
                else:
                    url_revision = f'https://sga.unemi.edu.ec/adm_configuracionpropuesta?action=tribunaltemas&idconfiguracion={eTemaTitulacionPosgradoMatricula.convocatoria_id}'
                for persona in ePersonasNotificar:
                    notificacion = Notificacion(
                        titulo='ACTAS DE SUSTENTACIÓN CON NOTAS FIRMADA POR TODOS LOS MIEMBROS DEL TRIBUNAL',
                        cuerpo='El acta de sustentación con notas ha sido firmada por todos, favor revisar en el módulo de proceso de titulación de posgrado.',
                        destinatario=persona,
                        url=url_revision,
                        content_type=None,
                        object_id=None,
                        prioridad=1,
                        app_label='SGA',
                        fecha_hora_visible=datetime.now() + timedelta(days=3))
                    notificacion.save(request)

            print("End proccess notification firma acta de sustentacion")
        except Exception as ex:
            pass

class notificar_persona_a_fimar_certificacion_defensa(threading.Thread):
    def     __init__(self, request, eTemaTitulacionPosgradoMatricula):
        self.request = request
        self.eTemaTitulacionPosgradoMatricula = eTemaTitulacionPosgradoMatricula
        threading.Thread.__init__(self)

    def run(self):
        try:
            CERTIFICACION_DEFENSA = 9
            print("start process notification firma acta de sustentacion")
            request, eTemaTitulacionPosgradoMatricula = self.request, self.eTemaTitulacionPosgradoMatricula
            eIntegranteFirmaTemaTitulacionPosgradoMatricula = eTemaTitulacionPosgradoMatricula.get_integrante_firman_por_tipo_acta(CERTIFICACION_DEFENSA)
            titulonotificacion = f"FIRMAR CERTIFICACIÓN DE LA DEFENSA: {eTemaTitulacionPosgradoMatricula.matricula.inscripcion}"
            cuerponotificacion = f"Certificación de la defensa listo para legalizar, favor firmar el acta por medio del SGA."

            for integrante in eIntegranteFirmaTemaTitulacionPosgradoMatricula:
                ePersona = integrante.persona
                if ePersona:
                    puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden_por_tipo(ePersona,CERTIFICACION_DEFENSA)
                    if puede:
                        url =f"https://sga.unemi.edu.ec/pro_tutoriaposgrado?action=firmardocumentostitulacionposgrado&tipo=certificaciondefensa&pk={eTemaTitulacionPosgradoMatricula.pk}"

                        notificacion = Notificacion(
                            titulo=titulonotificacion,
                            cuerpo=cuerponotificacion,
                            destinatario=ePersona,
                            url= url,
                            content_type=None,
                            object_id=None,
                            prioridad=1,
                            app_label='SGA',
                            fecha_hora_visible=datetime.now() + timedelta(days=3))
                        notificacion.save(request)
                        break


            if not eIntegranteFirmaTemaTitulacionPosgradoMatricula.filter(firmo=False):
                ids_notificar = variable_valor('ID_PERSONA_NOTIFICAR_ACTAS_FIRMADAS')
                ePersonasNotificar = Persona.objects.filter(status=True,pk__in=ids_notificar)
                if DEBUG:
                    url_revision = f'http://127.0.0.1:8000/adm_configuracionpropuesta?action=tribunaltemas&idconfiguracion={eTemaTitulacionPosgradoMatricula.convocatoria_id}'
                else:
                    url_revision = f'https://sga.unemi.edu.ec/adm_configuracionpropuesta?action=tribunaltemas&idconfiguracion={eTemaTitulacionPosgradoMatricula.convocatoria_id}'
                for persona in ePersonasNotificar:
                    notificacion = Notificacion(
                        titulo='CERTIFICACIÓN DE LA DEFENSA FIRMADA POR TODOS LOS MIEMBROS DEL TRIBUNAL',
                        cuerpo='Certificación de la defensa, ha sido firmada por todos, favor revisar en el módulo de proceso de titulación de posgrado.',
                        destinatario=persona,
                        url=url_revision,
                        content_type=None,
                        object_id=None,
                        prioridad=1,
                        app_label='SGA',
                        fecha_hora_visible=datetime.now() + timedelta(days=3))
                    notificacion.save(request)
            print("End proccess notification firma acta de sustentacion")
        except Exception as ex:
            pass

class generar_qr_graduaciones_posgrado_masivo(threading.Thread):
    def     __init__(self, request):
        self.request = request
        threading.Thread.__init__(self)

    def run(self):
        try:
            from posgrado.models import InscripcionEncuestaTitulacionPosgrado
            request = self.request
            eNotificacion = Notificacion(cuerpo=f'Generación masiva QR sedes de graduación',
                                         titulo=f'(En proceso) QR sedes de graduación masivo',
                                         destinatario=request.session.get('persona'),
                                         url='',
                                         prioridad=1,
                                         app_label='SGA',
                                         fecha_hora_visible=datetime.now() + timedelta(days=5),
                                         tipo=2,
                                         en_proceso=True)
            eNotificacion.save()

            print("start process genracion masiva qr sede de graduacion")

            id = int(request.POST.get('id', '0') or '0')
            contador = 1
            eInscripcionEncuestaTitulacionPosgrados = InscripcionEncuestaTitulacionPosgrado.objects.filter(encuestatitulacionposgrado_id=id, status=True, respondio=True, participa=True).exclude(asiento='',fila='',bloque='')
            for eInscripcionEncuestaTitulacionPosgrado in eInscripcionEncuestaTitulacionPosgrados:
                eInscripcionEncuestaTitulacionPosgrado.generar_qr_pdf_sede_graduacion(request)
                print(f"GENERANDO QR MASIVO GRADUACION POSGRADO {contador}/{eInscripcionEncuestaTitulacionPosgrados.count()}")
                contador+=1
            eNotificacion.titulo = f'(Finalizado) Generación Qr masiva sedes de graduación'
            eNotificacion.save()
            print("End proccess genracion masiva qr sede de graduacion")
        except Exception as ex:
            pass
