# -*- coding: latin-1 -*-
import cgi
import re
import threading

from datetime import datetime
from django.core.mail import get_connection, send_mail
from django.core.mail.message import EmailMessage
from django.template.context import Context
from django.template.loader import get_template

from settings import EMAIL_USE_TLS, EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD


def conectar_cuenta(cuenta):
    conectar = get_connection(use_tls=EMAIL_USE_TLS, host=EMAIL_HOST, port=EMAIL_PORT, username=cuenta, password=EMAIL_HOST_PASSWORD)
    return conectar


def conectar_cuenta2(cuenta):
    try:
        clave = 'Unemi2020**'
        conectar = get_connection(use_tls=EMAIL_USE_TLS, host=EMAIL_HOST, port=EMAIL_PORT, username=cuenta, password=clave)
        return conectar
    except Exception as ex:
        msg = ex.__str__()
        print(msg)
        return -1



class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, recipient_list, recipient_list_cc, adjuntos, cuenta):
        self.subject = subject
        self.recipient_list = recipient_list
        self.recipient_list_cc = recipient_list_cc
        self.html_content = html_content
        self.adjuntos = adjuntos
        self.cuenta = cuenta

        threading.Thread.__init__(self)

    def run(self):
        if self.recipient_list or self.recipient_list_cc:
            if self.cuenta:
                msg = EmailMessage(self.subject, self.html_content, self.cuenta, self.recipient_list, bcc=self.recipient_list_cc)
            else:
                msg = EmailMessage(self.subject, self.html_content, EMAIL_HOST_USER, self.recipient_list, bcc=self.recipient_list_cc)
            msg.content_subtype = "html"
            if self.adjuntos:
                for adjunto in self.adjuntos:
                    if type(adjunto) is str:
                        msg.attach_file(adjunto)
                    else:
                        msg.attach_file(adjunto.file.name)
            msg.send()


def send_html_mail(subject, html_template, data, recipient_list, recipient_list_cc, adjuntos=None, cuenta=None):
    try:
        if recipient_list.__len__() or recipient_list_cc.__len__():
            template = get_template(html_template)
            # if cuenta:
            #     # 1 = SGA - 2 = SAGEST - 3 = POSGRADO - 4 = POSTULATE - 5 = EMPLEO
            #     nombrecorreo_ = cuenta.split('@')[0]
            #     tiposistema_ = 1
            #     if 'sga' in nombrecorreo_:
            #         tiposistema_ = 1
            #     elif 'sagest' in nombrecorreo_:
            #         tiposistema_ = 2
            #     elif 'posgrado' in nombrecorreo_:
            #         tiposistema_ = 3
            #     elif 'postulate' in nombrecorreo_:
            #         tiposistema_ = 4
            #     elif 'empleo' in nombrecorreo_:
            #         tiposistema_ = 5
            #     data['tiposistema_'] = tiposistema_
            #
            #     from sga.models import AnalisisCuentasCorreos
            #     if AnalisisCuentasCorreos.objects.values("id").filter(cuenta=tiposistema_, fecha=datetime.now().date()).exists():
            #         analisis = AnalisisCuentasCorreos.objects.get(cuenta=tiposistema_, fecha=datetime.now().date())
            #         analisis.conteo += 1
            #         analisis.save(update_fields=['conteo'])
            #     else:
            #         analisis = AnalisisCuentasCorreos(cuenta=tiposistema_, fecha=datetime.now().date())
            #         analisis.save()
            d = (data)
            html_content = template.render(d)
            EmailThread(subject, html_content, recipient_list, recipient_list_cc, adjuntos, cuenta).start() #subject.lower().capitalize()
    except Exception as ex:
        pass


re_string = re.compile(r'(?P<htmlchars>[<&>])|(?P<space>^[ \t]+)|(?P<lineend>\r\n|\r|\n)|(?P<protocal>(^|\s)((http|ftp)://.*?))(\s|$)', re.S|re.M|re.I)


def plaintext2html(text, tabstop=4):
    def do_sub(m):
        c = m.groupdict()
        if c['htmlchars']:
            return cgi.escape(c['htmlchars'])
        if c['lineend']:
            return '<br>'
        elif c['space']:
            t = m.group().replace('\t', '&nbsp;' * tabstop)
            t = t.replace(' ', '&nbsp;')
            return t
        elif c['space'] == '\t':
            return ' ' * tabstop
        else:
            url = m.group('protocal')
            if url.startswith(' '):
                prefix = ' '
                url = url[1:]
            else:
                prefix = ''
            last = m.groups()[-1]
            if last in ['\n', '\r', '\r\n']:
                last = '<br>'
            return '%s<a href="%s">%s</a>%s' % (prefix, url, url, last)
    return re.sub(re_string, do_sub, text)