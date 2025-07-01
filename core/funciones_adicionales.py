import json
from decimal import Decimal

from django.http import HttpResponseRedirect

from settings import EMAIL_DOMAIN


def listar_packages_python():
    import pkg_resources
    installed_packages = pkg_resources.working_set
    installed_packages_list = sorted(["%s==%s" % (i.key, i.version)
                                      for i in installed_packages])
    print("\n".join(installed_packages_list))


def customgetattr(object, name):
    r = getattr(object, name)
    if str(type(r)) == "<class 'method'>" or str(type(r)) == "<class 'function'>":
        return r()
    return r


def get_verbose_name(app_label, model):
    from django.apps import apps
    try:
        return apps.get_model(app_label, model)._meta.verbose_name
    except LookupError:
        return None


def round_num_dec(value):
    return Decimal(value).quantize(Decimal(10) ** -2)

def redireccion_acceso(tipoentrada, META):
    if EMAIL_DOMAIN in META:
        if tipoentrada not in META:
            if 'sga' in META:
                return HttpResponseRedirect('/loginsga')
            elif 'admisionposgrado' in META:
                return HttpResponseRedirect('/loginposgrado')
            elif 'sagest' in META:
                return HttpResponseRedirect('/loginsagest')
            elif 'seleccionposgrado' in META:
                return HttpResponseRedirect('/loginpostulacion')
            elif 'postulate' in META:
                return HttpResponseRedirect('/loginpostulate')
            elif 'vinculacion' in META:
                return HttpResponseRedirect('/servicios')
