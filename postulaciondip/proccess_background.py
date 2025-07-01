import os
import io
import time
import threading
import unicodedata


from sga.funciones import generar_nombre
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import *

def get_acta_seleccion_docente_posgrado(self, request):
    try:
        from postulaciondip.models import ActaParalelo
        from postulaciondip.models import HistorialActaSeleccionDocente
        acta = self # Por si la funcion se llegara a mover de lugar.
        data, hoy = {}, datetime.now().date()
        data['acta'] = acta

        data['paralelos'] = ActaParalelo.objects.filter(acta=acta, status=True)
        hoy = datetime.now().date()
        name = unicodedata.normalize('NFD', u"%s. %s" % (acta.codigo, acta.comite.nombre)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
        filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
        filepath = u"actaselecciondocente/%s" % hoy.year
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'actaselecciondocente', hoy.year.__str__(), ''))
        os.makedirs(folder_pdf, exist_ok=True)
        data['pagesize'] = 'A4'
        data['request'] = request
        data['hoy'] = hoy
        self.fecha_generacion = hoy
        self.fecha_legalizacion = None
        self.save(request)
        if convert_html_to_pdf('adm_postulacion/docs/actaselecciondocente.html', data, filename, folder_pdf):
            self.archivo = os.path.join(filepath, filename)
            self.save(request)

            HistorialActaSeleccionDocente.objects.filter(acta=acta).update(status=False)
        return self.archivo.url if self.archivo else None
    except Exception as ex:
        raise NameError(u'Solicitud incorrecta. %s' % ex.__str__())


class notificar_convocatoria_posgrado(threading.Thread):

    def __init__(self, request,ePerfilComplatibles,eConvocatoria):
        self.request = request
        self.ePerfilComplatibles = ePerfilComplatibles
        self.eConvocatoria = eConvocatoria
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, ePerfilComplatibles,eConvocatoria = self.request, self.ePerfilComplatibles,self.eConvocatoria
        for perfil in ePerfilComplatibles:
            # Notifica el resultado del proceso como notificacion en el sga
            titulonotificacion = f"CONVOCATORIA SELECCIÓN DOCENTE DISPONIBLE"
            cuerponotificacion = f"Se ha aperturado convocatoria para contratación de docente para impartir clases para el módulo {eConvocatoria.titulo()}. Fecha de inicio: {eConvocatoria.fechainicio} - fecha fin {eConvocatoria.fechafin}"
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=perfil.persona,
                url=f"https://seleccionposgrado.unemi.edu.ec/loginpostulacion",
                content_type=None,
                object_id=None,
                prioridad=3,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save(request)
        print("End proccess notification")



class notificar_planificacion_completa_posgrado(threading.Thread):

    def __init__(self, request,eUsers,ePersonalApoyoMaestrias,eMateria):
        self.request = request
        self.eUsers = eUsers
        self.eMateria = eMateria
        self.ePersonalApoyoMaestrias = ePersonalApoyoMaestrias
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eUsers,eMateria,ePersonalApoyoMaestrias = self.request, self.eUsers,self.eMateria , self.ePersonalApoyoMaestrias
        if ePersonalApoyoMaestrias:
            for ePersona in ePersonalApoyoMaestrias:
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"PLANIFICACIÓN ACADÉMICA COMPLETA"
                cuerponotificacion = f"Se ha completado la planificación de la materia {eMateria}"
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona.personalapoyo.persona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=paralelos_planificacion&id={eMateria.asignaturamalla_id}&idp={eMateria.nivel.periodo_id}",
                    content_type=None,
                    object_id=None,
                    prioridad=2,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        else:

            for user in eUsers:
                ePersona = Persona.objects.filter(status=True,usuario=user).first()
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"PLANIFICACIÓN ACADÉMICA COMPLETA"
                cuerponotificacion = f"Se ha completado la planificación de la materia {eMateria}"
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=paralelos_planificacion&id={eMateria.asignaturamalla_id}&idp={eMateria.nivel.periodo_id}",
                    content_type=None,
                    object_id=None,
                    prioridad=2,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        print("End proccess notification")

class notificar_acta_revisada(threading.Thread):
    def __init__(self, request, eUsers,ePersonalApoyoMaestrias, eActaSeleccionDocente):
        self.request = request
        self.eUsers = eUsers
        self.ePersonalApoyoMaestrias = ePersonalApoyoMaestrias
        self.eActaSeleccionDocente = eActaSeleccionDocente
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eUsers, eActaSeleccionDocente,ePersonalApoyoMaestrias = self.request, self.eUsers, self.eActaSeleccionDocente , self.ePersonalApoyoMaestrias
        if ePersonalApoyoMaestrias:
            for ePersona in ePersonalApoyoMaestrias:
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"ACTA POR LEGALIZAR: {eActaSeleccionDocente}."
                cuerponotificacion = f"Se ha completado la revisión del acta de comité académico posgrado."
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona.personalapoyo.persona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        else:
            for user in eUsers:
                ePersona = Persona.objects.filter(status=True, usuario=user).first()
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"ACTA POR LEGALIZAR: {eActaSeleccionDocente}."
                cuerponotificacion = f"Se ha completado la revisión del acta de comité académico posgrado."
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        print("End proccess notification")

class notificar_acta_revisada_reprogramacion(threading.Thread):
    def __init__(self, request, eUsers,ePersonalApoyoMaestrias, eActaSeleccionDocente):
        self.request = request
        self.eUsers = eUsers
        self.ePersonalApoyoMaestrias = ePersonalApoyoMaestrias
        self.eActaSeleccionDocente = eActaSeleccionDocente
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eUsers, eActaSeleccionDocente,ePersonalApoyoMaestrias = self.request, self.eUsers, self.eActaSeleccionDocente , self.ePersonalApoyoMaestrias
        for integrante in eActaSeleccionDocente.get_integrante_comite():
            # Notifica el resultado del proceso como notificacion en el sga
            titulonotificacion = f"ACTA REPROGRAMACIÓN: {eActaSeleccionDocente}."
            cuerponotificacion = f"Se ha completado la revisión del acta de comité académico posgrado."
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=integrante.persona,
                url=f"https://sga.unemi.edu.ec/adm_postulacion?action=grupocomiteacademico&pk={eActaSeleccionDocente.pk}",
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save(request)

        if ePersonalApoyoMaestrias:
            for ePersona in ePersonalApoyoMaestrias:
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"ACTA REPROGRAMACIÓN: {eActaSeleccionDocente}."
                cuerponotificacion = f"Se ha completado la revisión del acta de comité académico posgrado."
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona.personalapoyo.persona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        else:
            for user in eUsers:
                ePersona = Persona.objects.filter(status=True, usuario=user).first()
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"ACTA POR LEGALIZAR: {eActaSeleccionDocente}."
                cuerponotificacion = f"Se ha completado la revisión del acta de comité académico posgrado."
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        print("End proccess notification")

class notificar_analistas_acta_firmada_completa(threading.Thread):
    def __init__(self, request, eUsers,ePersonalApoyoMaestrias, eActaSeleccionDocente):
        self.request = request
        self.eUsers = eUsers
        self.eActaSeleccionDocente = eActaSeleccionDocente
        self.ePersonalApoyoMaestrias = ePersonalApoyoMaestrias
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eUsers, eActaSeleccionDocente,ePersonalApoyoMaestrias = self.request, self.eUsers, self.eActaSeleccionDocente,self.ePersonalApoyoMaestrias
        if ePersonalApoyoMaestrias:
            for ePersona in ePersonalApoyoMaestrias:
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"ACTA COMPLETAMENTE LEGALIZADA: {eActaSeleccionDocente}."
                cuerponotificacion = f"Todos los miembros del comité han firmado."
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona.personalapoyo.persona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)

        else:
            for user in eUsers:
                ePersona = Persona.objects.filter(status=True, usuario=user).first()
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"ACTA COMPLETAMENTE LEGALIZADA: {eActaSeleccionDocente}."
                cuerponotificacion = f"Todos los miembros del comité han firmado."
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        print("End proccess notification")

class notificar_acta_para_ser_revisada(threading.Thread):
    def __init__(self, request, ePersonas, eActaSeleccionDocente):
        self.request = request
        self.ePersonas = ePersonas
        self.eActaSeleccionDocente = eActaSeleccionDocente
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, ePersonas, eActaSeleccionDocente = self.request, self.ePersonas, self.eActaSeleccionDocente
        for ePersona in ePersonas:
            # Notifica el resultado del proceso como notificacion en el sga
            titulonotificacion = f"ACTA CONFIGURADA, FAVOR REVISAR: {eActaSeleccionDocente}."
            cuerponotificacion = f"El acta de comité académico se encuentra 100% configurada y lista para su revisión."
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=ePersona,
                url=f"https://sga.unemi.edu.ec/seleccionprevia?pk={eActaSeleccionDocente.pk}",
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save(request)
        print("End proccess notification")

class notificar_persona_a_firmar(threading.Thread):
    def __init__(self, request, ePersona, eActaSeleccionDocente):
        self.request = request
        self.ePersona = ePersona
        self.eActaSeleccionDocente = eActaSeleccionDocente
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, ePersona, eActaSeleccionDocente = self.request, self.ePersona, self.eActaSeleccionDocente
        # Notifica el resultado del proceso como notificacion en el sga
        titulonotificacion = f"FIRMAR ACTA COMITÉ ACADÉMICO: {eActaSeleccionDocente}."
        cuerponotificacion = f"Acta lista para legalizar, favor firmar el acta por medio del SGA."
        notificacion = Notificacion(
            titulo=titulonotificacion,
            cuerpo=cuerponotificacion,
            destinatario=ePersona,
            url=f"https://sga.unemi.edu.ec/adm_postulacion?action=firmaractaselecciondocente&pk={eActaSeleccionDocente.pk}",
            content_type=None,
            object_id=None,
            prioridad=1,
            app_label='SGA',
            fecha_hora_visible=datetime.now() + timedelta(days=3))
        notificacion.save(request)
        print("End proccess notification")

class proceso_notificar_votacion_comite(threading.Thread):
    def __init__(self, request, eIntegranteComiteAcademicoPosgrado, eActaSeleccionDocente):
        self.request = request
        self.eIntegranteComiteAcademicoPosgrado = eIntegranteComiteAcademicoPosgrado
        self.eActaSeleccionDocente = eActaSeleccionDocente
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eActaSeleccionDocente, eIntegranteComiteAcademicoPosgrado = self.request, self.eActaSeleccionDocente, self.eIntegranteComiteAcademicoPosgrado
        # Notifica el resultado del proceso como notificacion en el sga
        titulonotificacion = f"Votación comité: {eActaSeleccionDocente}."
        cuerponotificacion = f"Votación habilitada realizar  el proceso por medio del SGA."

        for integrante in eIntegranteComiteAcademicoPosgrado:
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=integrante.persona,
                url=f"https://sga.unemi.edu.ec/adm_postulacion?action=grupocomiteacademico&revisar_acta={eActaSeleccionDocente.pk}",
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save(request)
        print("End proccess notification")

class notificar_analistas_estado_invitacion(threading.Thread):
    def __init__(self, request, eUsers,ePersonalApoyoMaestrias,eInscripcionInvitacion):
        self.request = request
        self.eUsers = eUsers
        self.ePersonalApoyoMaestrias = ePersonalApoyoMaestrias
        self.eInscripcionInvitacion = eInscripcionInvitacion
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eUsers,ePersonalApoyoMaestrias, eInscripcionInvitacion = self.request, self.eUsers,self.ePersonalApoyoMaestrias, self.eInscripcionInvitacion
        titulonotificacion = f"ESTADO INVITACIÓN: {eInscripcionInvitacion.actaparalelo}."
        cuerponotificacion = ''
        if eInscripcionInvitacion.estadoinvitacion == 5:#rechazada
            cuerponotificacion = f"El postulante ha rechazado la invitación."

        if eInscripcionInvitacion.estadoinvitacion  == 4:#aceptada
            cuerponotificacion = f"El postulante ha aceptado la invitación."


        if ePersonalApoyoMaestrias:
            for ePersona in ePersonalApoyoMaestrias:
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona.personalapoyo.persona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=contratacion&id={eInscripcionInvitacion.actaparalelo.acta_id}&cv={eInscripcionInvitacion.inscripcion.convocatoria.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)

        else:
            for user in eUsers:
                ePersona = Persona.objects.filter(status=True, usuario=user).first()
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=contratacion&id={eInscripcionInvitacion.actaparalelo.acta_id}&cv={eInscripcionInvitacion.inscripcion.convocatoria.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        print("End proccess notification")

class notificar_realizar_votacion_director_posgrado(threading.Thread):
    def __init__(self, request, eActaParalelo):
        self.request = request
        self.eActaParalelo = eActaParalelo
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request,eActaParalelo = self.request, self.eActaParalelo
        eActaSeleccionDocente = eActaParalelo.acta
        ePersona = eActaParalelo.get_miembro_comite_director_posgrado().persona
        # Notifica el resultado del proceso como notificacion en el sga
        titulonotificacion = f"REALIZAR VOTACION: {eActaSeleccionDocente}."
        cuerponotificacion = f"Es su turno de realizar la votación para el paralelo"
        notificacion = Notificacion(
            titulo=titulonotificacion,
            cuerpo=cuerponotificacion,
            destinatario=ePersona,
            url=f"https://sga.unemi.edu.ec/adm_postulacion?action=grupocomiteacademico&paralelo_id={eActaParalelo.pk}",
            content_type=None,
            object_id=None,
            prioridad=1,
            app_label='SGA',
            fecha_hora_visible=datetime.now() + timedelta(days=3))
        notificacion.save(request)
        print("End proccess notification")


class notificar_analistas_acta_votacion_completa(threading.Thread):
    def __init__(self, request, eUsers,ePersonalApoyoMaestrias, eActaSeleccionDocente):
        self.request = request
        self.eUsers = eUsers
        self.eActaSeleccionDocente = eActaSeleccionDocente
        self.ePersonalApoyoMaestrias = ePersonalApoyoMaestrias
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eUsers, eActaSeleccionDocente,ePersonalApoyoMaestrias = self.request, self.eUsers, self.eActaSeleccionDocente,self.ePersonalApoyoMaestrias

        try:
            get_acta_seleccion_docente_posgrado(self=eActaSeleccionDocente,request=request)
        except Exception as ex:
            pass


        if ePersonalApoyoMaestrias:
            for ePersona in ePersonalApoyoMaestrias:
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"ACTA VOTACIÓN COMPLETA: {eActaSeleccionDocente}."
                cuerponotificacion = f"Todos los miembros del comité han votado en cada paralelo."
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona.personalapoyo.persona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)

        else:
            for user in eUsers:
                ePersona = Persona.objects.filter(status=True, usuario=user).first()
                # Notifica el resultado del proceso como notificacion en el sga
                titulonotificacion = f"ACTA COMPLETAMENTE LEGALIZADA: {eActaSeleccionDocente}."
                cuerponotificacion = f"Todos los miembros del comité han firmado."
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        print("End proccess notification")

class actualizar_acta_seleccion_docente(threading.Thread):
    def __init__(self, request, eActaSeleccionDocente):
        self.request = request
        self.eActaSeleccionDocente = eActaSeleccionDocente
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eActaSeleccionDocente= self.request, self.eActaSeleccionDocente
        try:
            get_acta_seleccion_docente_posgrado(self=eActaSeleccionDocente,request=request)
        except Exception as ex:
            pass
        print("End proccess notification")

class notificar_analistas_requisitos_subidos_por_personal_a_contratar(threading.Thread):
    def __init__(self, request, eUsers,ePersonalApoyoMaestrias,eInscripcionInvitacion):
        self.request = request
        self.eUsers = eUsers
        self.ePersonalApoyoMaestrias = ePersonalApoyoMaestrias
        self.eInscripcionInvitacion = eInscripcionInvitacion
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eUsers,ePersonalApoyoMaestrias, eInscripcionInvitacion = self.request, self.eUsers,self.ePersonalApoyoMaestrias, self.eInscripcionInvitacion
        titulonotificacion = f"Requisitos cargados: {eInscripcionInvitacion.get_personal_a_contratar()}."
        cuerponotificacion = f"El postulante ha subido todos los requisitos para contratación."


        if ePersonalApoyoMaestrias:
            for ePersona in ePersonalApoyoMaestrias:
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona.personalapoyo.persona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=revision_requisitos_personal_a_contratar&id={eInscripcionInvitacion.get_personal_a_contratar().pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)

        else:
            for user in eUsers:
                ePersona = Persona.objects.filter(status=True, usuario=user).first()
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=revision_requisitos_personal_a_contratar&id={eInscripcionInvitacion.get_personal_a_contratar().pk}",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        print("End proccess notification")


#procesos informe de contratacion
class actualizar_informe_de_contratacion_posgrado(threading.Thread):
    def __init__(self, request, eInformeContratacion):
        self.request = request
        self.eInformeContratacion = eInformeContratacion
        threading.Thread.__init__(self)

    def run(self):
        print("start process generacion informe contratacion posgrado")
        request, eInformeContratacion= self.request, self.eInformeContratacion
        try:
            eInformeContratacion.guardar_con_secuencia_archivo_informe_contratacion(request)
        except Exception as ex:
            pass
        print("End proccess generacion informe contratacion posgrado")

class actualizar_memo_informe_de_contratacion_posgrado(threading.Thread):
    def __init__(self, request, eInformeContratacion):
        self.request = request
        self.eInformeContratacion = eInformeContratacion
        threading.Thread.__init__(self)

    def run(self):
        print("start process generacion de memo informe de contratacion posgrado")
        request, eInformeContratacion= self.request, self.eInformeContratacion
        try:
            eInformeContratacion.guardar_con_secuencia_archivo_memo_contratacion(request)

        except Exception as ex:
            pass
        print("End proccess generacion de memo informe de contratacion posgrado")

class notificar_persona_a_fimar_informe_contratacion(threading.Thread):
    def     __init__(self, request, eInformeContratacion):
        self.request = request
        self.eInformeContratacion = eInformeContratacion
        threading.Thread.__init__(self)

    def run(self):
        print("start process notification")
        request, eInformeContratacion = self.request, self.eInformeContratacion
        eInformeContratacionIntegrantesFirma = eInformeContratacion.get_integrantes_firman()
        titulonotificacion = f"FIRMAR INFORME DE CONTRATACIÓN: {eInformeContratacion.get_documento_informe().codigo}"
        cuerponotificacion = f"informe de contratación listo para legalizar, favor firmar el acta por medio del SGA."

        for integrante in eInformeContratacionIntegrantesFirma:
            ePersona = integrante.persona
            if ePersona:
                puede, mensaje = eInformeContratacion.puede_firmar_integrante_segun_orden(ePersona)
                if puede:
                    if eInformeContratacion.persona_es_quien_firma_informe_memo(integrante.pk):
                        url =f"https://sga.unemi.edu.ec/adm_postulacion?action=firmarinformecontratacion"

                    else:
                        url =f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoinformes&pk={eInformeContratacion.pk}"

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

        print("End proccess notification")

class proceso_guardado_principal_alternos_de_todas_las_convocatorias_de_los_paralelos(threading.Thread):
    def __init__(self, request, eActaSeleccionDocente,eUsers):
        self.request = request
        self.eActaSeleccionDocente = eActaSeleccionDocente
        self.eUsers = eUsers
        threading.Thread.__init__(self)

    def run(self):
        print("start process guardado principal - alternos")
        request, eActaSeleccionDocente,eUsers = self.request, self.eActaSeleccionDocente,self.eUsers
        print("inicio guardado principal")
        for eActaParalelo in eActaSeleccionDocente.get_convocatorias():
            eActaParalelo.get_personal().update(status=False)

        for eActaParalelo in eActaSeleccionDocente.get_convocatorias():
            eActaParalelo.guardar_automatico_principales_de_toda_el_acta(request)
        print("End  guardado principal")
        print("Inicio  guardado alternos")
        for eActaParalelo in eActaSeleccionDocente.get_convocatorias():
            eActaParalelo.guardar_automatico_alternos_banco_elegible_de_toda_el_acta(request)
        print("End proccess guardado principal- alternos")

        for user in eUsers:
            ePersona = Persona.objects.filter(status=True, usuario=user).first()

            if DEBUG:
                url = f"http://127.0.0.1:8000/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}"
            else:
                url = f"https://sga.unemi.edu.ec/adm_postulacion?action=listadoactas&pk={eActaSeleccionDocente.pk}"
            titulonotificacion = f"Baremo completo - {eActaSeleccionDocente}"
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=f"Votaciones completas {eActaSeleccionDocente} ",
                destinatario=ePersona,
                url=url,
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save(request)
