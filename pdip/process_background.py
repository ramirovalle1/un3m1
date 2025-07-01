import threading
from sga.models import *
from settings import DEBUG
from sga.templatetags.sga_extras import encrypt
#procesos informe de contratacion
class actualizar_acta_pago_posgrado(threading.Thread):
    def __init__(self, request, eActaPagoPosgrado):
        self.request = request
        self.eActaPagoPosgrado = eActaPagoPosgrado
        threading.Thread.__init__(self)

    def run(self):
        print("start process acta pago posgrado posgrado")
        request, eActaPagoPosgrado= self.request, self.eActaPagoPosgrado
        try:
            eActaPagoPosgrado.generar_actualizar_check_list_pago_pdf(request)
            eActaPagoPosgrado.generar_actualizar_acta_pago_pdf(request)
            eActaPagoPosgrado.generar_actualizar_memo_pago_pdf(request)
        except Exception as ex:
            pass
        print("End proccess generacion acta pago posgrado")

class actualizar_todas_las_solicitudes_orden_and_opcional_de_todos_los_requisitos_de_pago(threading.Thread):
    def __init__(self, request, eGrupoRequisitoPago):
        self.request = request
        self.eGrupoRequisitoPago = eGrupoRequisitoPago
        threading.Thread.__init__(self)

    def run(self):
        print("start process actualizar orden y tipo opcional de todas las solicitudes en los requisitos de pago")
        request, eGrupoRequisitoPago= self.request, self.eGrupoRequisitoPago
        try:
            from pdip.models import RequisitoSolicitudPago
            for eRequisitoPagoGrupoRequisito in eGrupoRequisitoPago.get_requisitos():
                RequisitoSolicitudPagoExistentes= RequisitoSolicitudPago.objects.filter(status=True, requisito=eRequisitoPagoGrupoRequisito.requisitopagodip)
                if RequisitoSolicitudPagoExistentes.exists():
                    for eRequisitoSolicitudPagoExistente in RequisitoSolicitudPagoExistentes:
                        eRequisitoSolicitudPagoExistente.orden = eRequisitoPagoGrupoRequisito.orden
                        eRequisitoSolicitudPagoExistente.opcional =eRequisitoPagoGrupoRequisito.opcional
                        eRequisitoSolicitudPagoExistente.save(request)

        except Exception as ex:
            pass
        print("End proccess  actulizar orden y tipo opcional de todas las solicitudes en los requisitos de pago")

class notificar_persona_a_fimar_acta_pago(threading.Thread):
    def     __init__(self, request, eActaPagoPosgrado):
        self.request = request
        self.eActaPagoPosgrado = eActaPagoPosgrado
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eActaPagoPosgrado = self.request, self.eActaPagoPosgrado
        eActaPagoIntegrantesFirma = eActaPagoPosgrado.get_integrantes_firman()
        titulonotificacion = f"FIRMAR ACTA DE PAGO: {eActaPagoPosgrado.codigo}"
        cuerponotificacion = f"Acta de pago listo para legalizar, favor firmar el acta por medio del SGA."

        for integrante in eActaPagoIntegrantesFirma:
            ePersona = integrante.persona
            if ePersona:
                puede, mensaje = eActaPagoPosgrado.puede_firmar_integrante_segun_orden(ePersona)
                if puede:
                    if DEBUG:
                        url =f"http://127.0.0.1:8000/adm_solicitudpago?action=firmaractapago&pk={eActaPagoPosgrado.pk}"
                    else:
                        url =f"https://sga.unemi.edu.ec/adm_solicitudpago?action=firmaractapago&pk={eActaPagoPosgrado.pk}"

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

        if not eActaPagoIntegrantesFirma.filter(firmo=False).exists():
            if DEBUG:
                url = f"http://127.0.0.1:8000/adm_solicitudpago?action=view_actas_pago&pk={eActaPagoPosgrado.pk}"
            else:
                url = f"https://sga.unemi.edu.ec/adm_solicitudpago?action=view_actas_pago&pk={eActaPagoPosgrado.pk}"

            notificacion = Notificacion(
                titulo=f'Acta de pago: {eActaPagoPosgrado.codigo} legalizada por todos.',
                cuerpo=f'Acta de pago: {eActaPagoPosgrado.codigo}  legalizada por todos los integrantes.',
                destinatario=eActaPagoPosgrado.get_persona_elabora(),
                url=url,
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save(request)

        print("End proccess notification")

class notificar_subir_factura_profesionales(threading.Thread):
    def     __init__(self, request, eActaPagoPosgrado):
        self.request = request
        self.eActaPagoPosgrado = eActaPagoPosgrado
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eActaPagoPosgrado = self.request, self.eActaPagoPosgrado
        eSolicitudPago = eActaPagoPosgrado.get_detalle_solicitudes()

        cuerponotificacion = f"Subir la factura para su proceso de pago por medio del SGA."

        for integrante in eSolicitudPago:
            ePersona = integrante.solicitudpago.contrato.persona
            if ePersona:
                if DEBUG:
                    url =f"http://127.0.0.1:8000/pro_solicitudpago?action=requisitos_solicitudes_pagos&id={encrypt(integrante.solicitudpago.pk)}"
                else:
                    url =f"https://sga.unemi.edu.ec/pro_solicitudpago?action=requisitos_solicitudes_pagos&id={encrypt(integrante.solicitudpago.pk)}"
                titulonotificacion = f"SUBIR FACTURA DE PAGO - MES {integrante.solicitudpago.get_str_meses_entre_fechas_inicio_fin()}"
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

        print("End proccess notification")


class notificar_contrato_subido_para_registrar_analista_validador(threading.Thread):
    def     __init__(self, request, ePersonas):
        self.request = request
        self.ePersonas = ePersonas
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, ePersonas = self.request, self.ePersonas
        cuerponotificacion = f"Se registro un nuevo contrato"

        for ePersona in ePersonas:
            if ePersona:
                if DEBUG:
                    url =f"http://127.0.0.1:8000/adm_solicitudpago?action=viewcontratossinasignar"
                else:
                    url =f"https://sga.unemi.edu.ec/adm_solicitudpago?action=viewcontratossinasignar"

                titulonotificacion = f"Se registro un nuevo contrato"
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

        print("End proccess notification")
