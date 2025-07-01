#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from django.db import transaction
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *
from Moodle_Funciones import crearhtmlphpmoodle, crearhtmlphpmoodleadmision

urlerror = ["""<html>
<head><title>502 Bad Gateway</title></head>
<body>
<center><h1>502 Bad Gateway</h1></center>
<hr><center>nginx/1.20.1</center>
</body>
</html>
""",
            """
<html><head>
<meta http-equiv="content-type" content="text/html;charset=utf-8">
<title>502 Server Error</title>
</head>
<body text=#000000 bgcolor=#ffffff>
<h1>Error: Server Error</h1>
<h2>The server encountered a temporary error and could not complete your request.<p>Please try again in 30 seconds.</h2>
<h2></h2>
</body></html>
""",
            """<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>500 Internal Server Error</title>
</head><body>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error or
misconfiguration and was unable to complete
your request.</p>
<p>Please contact the server administrator at 
 root@localhost to inform them of the time this error occurred,
 and the actions you performed just before this error.</p>
<p>More information about this error may be available
in the server error log.</p>
</body></html>
""",
            """<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- The above 3 meta tags *must* come first in the head; any other head content must come *after* these tags -->

    <title>500 SERVER ERROR</title>

    <!-- Google font -->
    <link href="https://fonts.googleapis.com/css?family=Cabin:400,700" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:900" rel="stylesheet">

    <!-- Custom stlylesheet -->

    <!-- HTML5 shim and Respond.js for IE8 support of HTML5 elements and media queries -->
    <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
    <!--[if lt IE 9]>
    <script src="https://oss.maxcdn.com/html5shiv/3.7.3/html5shiv.min.js"></script>
    <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
    <![endif]-->

</head>

<style>
    * {
        -webkit-box-sizing: border-box;
        box-sizing: border-box;
    }

    body {
        padding: 0;
        margin: 0;
    }

    #notfound {
        position: relative;
        height: 100vh;
    }

    #notfound .notfound {
        position: absolute;
        left: 50%;
        top: 50%;
        -webkit-transform: translate(-50%, -50%);
        -ms-transform: translate(-50%, -50%);
        transform: translate(-50%, -50%);
    }

    .notfound {
        max-width: 520px;
        width: 100%;
        line-height: 1.4;
        text-align: center;
    }

    .notfound .notfound-404 {
        position: relative;
        height: 240px;
    }

    .notfound .notfound-404 h1 {
        font-family: 'Montserrat', sans-serif;
        position: absolute;
        left: 50%;
        top: 50%;
        -webkit-transform: translate(-50%, -50%);
        -ms-transform: translate(-50%, -50%);
        transform: translate(-50%, -50%);
        font-size: 252px;
        font-weight: 900;
        margin: 0px;
        color: #262626;
        text-transform: uppercase;
        letter-spacing: -40px;
        margin-left: -20px;
    }

    .notfound .notfound-404 h1 > span {
        text-shadow: -8px 0px 0px #fff;
    }

    .notfound .notfound-404 h3 {
        font-family: 'Cabin', sans-serif;
        position: relative;
        font-size: 16px;
        font-weight: 700;
        text-transform: uppercase;
        color: #262626;
        margin: 0px;
        letter-spacing: 3px;
        padding-left: 6px;
    }

    .notfound h2 {
        font-family: 'Cabin', sans-serif;
        font-size: 20px;
        font-weight: 400;
        text-transform: uppercase;
        color: #000;
        margin-top: 0px;
        margin-bottom: 25px;
    }

    @media only screen and (max-width: 767px) {
        .notfound .notfound-404 {
            height: 200px;
        }

        .notfound .notfound-404 h1 {
            font-size: 200px;
        }
    }

    @media only screen and (max-width: 480px) {
        .notfound .notfound-404 {
            height: 162px;
        }

        .notfound .notfound-404 h1 {
            font-size: 162px;
            height: 150px;
            line-height: 162px;
        }

        .notfound h2 {
            font-size: 16px;
        }
    }

</style>

<body>

<div id="notfound">
    <div class="notfound">
        <div class="notfound-404">
            <h1><span>5</span><span>0</span><span>0</span></h1>
        </div>
        <h2>lo sentimos, ha ocurrido un error en el servidor</h2>
        <a href="/"><h2>Regresar</h2></a>
    </div>
</div>

</body><!-- This templates was made by Colorlib (https://colorlib.com) -->

</html>
"""
            ]
import sys
periodospregrado = [317]
for materia in Materia.objects.filter(actualizarhtml=True, status=True, nivel__periodo_id__in=periodospregrado, asignaturamalla__malla__carrera__coordinacion__id=1):
    try:
        if materia.coordinacion().id != 9:
            crearhtmlphpmoodle(materia)
        else:
            crearhtmlphpmoodleadmision(materia)
    except Exception as ex:
        print('Error al crear html %s ---- %s ----- %s' % (ex, materia,  sys.exc_info()[-1].tb_lineno))


for materia in Materia.objects.filter(status=True, nivel__periodo_id__in=periodospregrado, asignaturamalla__malla__carrera__coordinacion__id=1):
    try:
        if materia.urlhtml:
            with open(materia.urlhtml) as f:
                a = f.read()
            f.close()
            if a == urlerror[0] or a == urlerror[1] or a == urlerror[2] or a == urlerror[3]:
                print("Encontramos un error lo vamos a corregir por ti")
                if materia.coordinacion().id != 9:
                    crearhtmlphpmoodle(materia)
                else:
                    crearhtmlphpmoodleadmision(materia)
                # crearhtmlphpmoodle(materia)
    except Exception as ex:
        print('Error al crear html %s ---- %s ---- %s' % (ex, materia,  sys.exc_info()[-1].tb_lineno))

# for materia in Materia.objects.filter(actualizarhtml=True, status=True, nivel__periodo_id=202, asignaturamalla__malla__carrera__coordinacion__id=9):
#     try:
#         print("%s - %s" % (materia, materia.idcursomoodle))
#         crearhtmlphpmoodleadmision(materia)
#     except Exception as ex:
#         print('Error al crear html %s ---- %s' % (ex, materia.idcursomoodle))
