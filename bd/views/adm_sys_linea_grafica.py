# -*- coding: UTF-8 -*-
import random
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from bd.models import LogQuery
from decorators import secure_module, last_access
from bd.forms import *
from settings import MEDIA_ROOT, MEDIA_URL
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery
import xlwt
from xlwt import *
import io
import xlsxwriter

@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['title'] = f'Documentación línea gráfica'

    if request.method == 'GET':
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'accordions':
                request.session['viewactivo'] = 2
                return render(request, "lineagrafica/accordions.html", data)

            if action == 'alerts':
                request.session['viewactivo'] = 3
                return render(request, "lineagrafica/alerts.html", data)

            if action == 'avatar':
                request.session['viewactivo'] = 4
                return render(request, "lineagrafica/avatar.html", data)

            if action == 'badge':
                request.session['viewactivo'] = 5
                return render(request, "lineagrafica/badge.html", data)

            if action == 'breadcrumb':
                request.session['viewactivo'] = 6
                return render(request, "lineagrafica/breadcrumb.html", data)

            if action == 'buttons':
                request.session['viewactivo'] = 7
                return render(request, "lineagrafica/buttons.html", data)

            if action == 'button-group':
                request.session['viewactivo'] = 8
                return render(request, "lineagrafica/button-group.html", data)

            if action == 'card':
                request.session['viewactivo'] = 9
                return render(request, "lineagrafica/card.html", data)

            if action == 'carousel':
                request.session['viewactivo'] = 10
                return render(request, "lineagrafica/carousel.html", data)

            if action == 'close-button':
                request.session['viewactivo'] = 11
                return render(request, "lineagrafica/close-button.html", data)

            if action == 'collapse':
                request.session['viewactivo'] = 12
                return render(request, "lineagrafica/collapse.html", data)

            if action == 'dropdowns':
                request.session['viewactivo'] = 13
                return render(request, "lineagrafica/dropdowns.html", data)

            if action == 'images':
                request.session['viewactivo'] = 14
                return render(request, "lineagrafica/images.html", data)

            if action == 'list-group':
                request.session['viewactivo'] = 15
                return render(request, "lineagrafica/list-group.html", data)

            if action == 'modal':
                request.session['viewactivo'] = 16
                return render(request, "lineagrafica/modal.html", data)

            if action == 'navs-tabs':
                request.session['viewactivo'] = 17
                return render(request, "lineagrafica/navs-tabs.html", data)

            if action == 'navbar':
                request.session['viewactivo'] = 18
                return render(request, "lineagrafica/navbar.html", data)

            if action == 'offcanvas':
                request.session['viewactivo'] = 19
                return render(request, "lineagrafica/offcanvas.html", data)

            if action == 'pagination':
                request.session['viewactivo'] = 20
                return render(request, "lineagrafica/pagination.html", data)

            if action == 'placeholders':
                request.session['viewactivo'] = 21
                return render(request, "lineagrafica/placeholders.html", data)

            if action == 'popovers':
                request.session['viewactivo'] = 22
                return render(request, "lineagrafica/popovers.html", data)

            if action == 'progress':
                request.session['viewactivo'] = 23
                return render(request, "lineagrafica/progress.html", data)

            if action == 'scrollspy':
                request.session['viewactivo'] = 24
                return render(request, "lineagrafica/scrollspy.html", data)

            if action == 'spinners':
                request.session['viewactivo'] = 25
                return render(request, "lineagrafica/spinners.html", data)

            if action == 'tables':
                request.session['viewactivo'] = 26
                return render(request, "lineagrafica/tables.html", data)

            if action == 'toasts':
                request.session['viewactivo'] = 27
                return render(request, "lineagrafica/toasts.html", data)

            if action == 'tooltips':
                request.session['viewactivo'] = 28
                return render(request, "lineagrafica/tooltips.html", data)

            if action == 'basic_forms':
                request.session['viewactivo'] = 29
                return render(request, "lineagrafica/basic_forms.html", data)

            if action == 'advance_forms':
                request.session['viewactivo'] = 30
                return render(request, "lineagrafica/advance_forms.html", data)

            if action == 'bootstrap_select':
                request.session['viewactivo'] = 31
                return render(request, "lineagrafica/bootstrap_select.html", data)

            if action == 'dropzone':
                request.session['viewactivo'] = 32
                return render(request, "lineagrafica/dropzone.html", data)

            if action == 'datepicker':
                request.session['viewactivo'] = 33
                return render(request, "lineagrafica/datepicker.html", data)

            if action == 'input_group':
                request.session['viewactivo'] = 34
                return render(request, "lineagrafica/input_group.html", data)

            if action == 'inputmask':
                request.session['viewactivo'] = 35
                return render(request, "lineagrafica/inputmask.html", data)

            if action == 'quill_editor':
                request.session['viewactivo'] = 36
                return render(request, "lineagrafica/quill_editor.html", data)

            if action == 'Tagify':
                request.session['viewactivo'] = 37
                return render(request, "lineagrafica/Tagify.html", data)

            if action == 'accordions-snippet':
                request.session['viewactivo'] = 38
                return render(request, "lineagrafica/accordions-snippet.html", data)

            if action == 'card-snippet':
                request.session['viewactivo'] = 39
                return render(request, "lineagrafica/card-snippet.html", data)

            if action == 'chart':
                request.session['viewactivo'] = 40
                return render(request, "lineagrafica/chart.html", data)

            if action == 'clients':
                request.session['viewactivo'] = 41
                return render(request, "lineagrafica/clients.html", data)

            if action == 'cta':
                request.session['viewactivo'] = 42
                return render(request, "lineagrafica/cta.html", data)

            if action == 'features':
                request.session['viewactivo'] = 43
                return render(request, "lineagrafica/features.html", data)

            if action == 'hero':
                request.session['viewactivo'] = 44
                return render(request, "lineagrafica/hero.html", data)

            if action == 'image-snippet':
                request.session['viewactivo'] = 45
                return render(request, "lineagrafica/image-snippet.html", data)

            if action == 'intigrations':
                request.session['viewactivo'] = 46
                return render(request, "lineagrafica/intigrations.html", data)

            if action == 'pricing':
                request.session['viewactivo'] = 47
                return render(request, "lineagrafica/pricing.html", data)

            if action == 'reviews':
                request.session['viewactivo'] = 48
                return render(request, "lineagrafica/reviews.html", data)

            if action == 'slider':
                request.session['viewactivo'] = 49
                return render(request, "lineagrafica/slider.html", data)

            if action == 'stats':
                request.session['viewactivo'] = 50
                return render(request, "lineagrafica/stats.html", data)

            if action == 'tables_snippet':
                request.session['viewactivo'] = 51
                return render(request, "lineagrafica/tables_snippet.html", data)

            if action == 'team':
                request.session['viewactivo'] = 52
                return render(request, "lineagrafica/team.html", data)

            if action == 'testimonials':
                request.session['viewactivo'] = 53
                return render(request, "lineagrafica/testimonials.html", data)

            if action == 'user-profile':
                request.session['viewactivo'] = 54
                return render(request, "lineagrafica/user-profile.html", data)

            if action == 'background':
                request.session['viewactivo'] = 55
                return render(request, "lineagrafica/background.html", data)

            if action == 'borders':
                request.session['viewactivo'] = 56
                return render(request, "lineagrafica/borders.html", data)

            if action == 'colored-links':
                request.session['viewactivo'] = 57
                return render(request, "lineagrafica/colored-links.html", data)

            if action == 'opacity':
                request.session['viewactivo'] = 58
                return render(request, "lineagrafica/opacity.html", data)

            if action == 'ratios':
                request.session['viewactivo'] = 59
                return render(request, "lineagrafica/ratios.html", data)

            if action == 'stacks':
                request.session['viewactivo'] = 60
                return render(request, "lineagrafica/stacks.html", data)

            if action == 'text-colors':
                request.session['viewactivo'] = 61
                return render(request, "lineagrafica/text-colors.html", data)

            if action == 'text':
                request.session['viewactivo'] = 62
                return render(request, "lineagrafica/text.html", data)

            if action == 'text-truncation':
                request.session['viewactivo'] = 63
                return render(request, "lineagrafica/text-truncation.html", data)

            if action == 'vertical-rule':
                request.session['viewactivo'] = 64
                return render(request, "lineagrafica/vertical-rule.html", data)

            if action == 'x-editable':
                request.session['viewactivo'] = 65
                return render(request, "lineagrafica/x-editable.html", data)

            if action == 'buttons_options':
                request.session['viewactivo'] = 66
                return render(request, "lineagrafica/buttons_options.html", data)
    try:
        request.session['viewactivo'] = 1
        return render(request, "lineagrafica/view.html", data)
    except Exception as ex:
        pass
