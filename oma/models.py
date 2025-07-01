import time
from django.db import models, connection, connections
from sga.funciones import ModeloBase, null_to_decimal, null_to_numeric, convertir_fecha
from django.db.models import Q
from django.db.models.query import QuerySet
from datetime import datetime, timedelta, date
from django.contrib.auth.models import User, Group

from sga.models import HistoricoRecordAcademico

ESTADOS_ASIGNATURA_INSCRIPCION_CURSO = (
    (0, u'PENDIENTE'),
    (1, u'APROBADO'),
    (2, u'REPROBADO')
)

PARCIAL = (
    (0, u'---------'),
    (1, u'PARCIAL 1'),
    (2, u'PARCIAL 2')
)


# Create your models here.
class ModeloEvaluativo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    fecha = models.DateField(verbose_name=u"Fecha")
    principal = models.BooleanField(default=False, verbose_name=u"Principal")
    notamaxima = models.FloatField(default=0, verbose_name=u'Nota maxima')
    notaaprobar = models.FloatField(default=0, verbose_name=u'Nota para aprobar')
    notarecuperacion = models.FloatField(default=0, verbose_name=u'Nota para recuperación')
    asistenciaaprobar = models.FloatField(default=0, verbose_name=u'Asistencia para aprobar')
    asistenciarecuperacion = models.FloatField(default=0, verbose_name=u'Asistencia para recuperación')
    observaciones = models.TextField(default='', max_length=200, verbose_name=u'Observaciones')
    logicamodelo = models.TextField(default='', verbose_name=u'logica')
    notafinaldecimales = models.IntegerField(default=0, verbose_name=u'lugares decimales')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Modelo evaluativo"
        verbose_name_plural = u"Modelos evaluativos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def en_uso(self):
        return self.curso_set.filter(status=True).exists()

    def campos(self):
        return self.detallemodeloevaluativo_set.filter(status=True).order_by('orden')

    def campos2(self):
        return self.detallemodeloevaluativo_set.filter(status=True).order_by('orden').first()

    def campos_editables(self):
        return self.detallemodeloevaluativo_set.filter(dependiente=False, status=True)

    def campos_editables1(self):
        return self.detallemodeloevaluativo_set.filter((Q(nombre__icontains='N') | Q(nombre__icontains='T')),
                                                       dependiente=False, status=True)
        # return self.detallemodeloevaluativo_set.filter(dependiente=False, nombre__contains='N')

    def campo(self, nombre):
        return self.detallemodeloevaluativo_set.filter(nombre=nombre, status=True)[0] if self.detallemodeloevaluativo_set.values(
            "id").filter(nombre=nombre, status=True).exists() else None

    def campos_dependientes(self):
        return self.detallemodeloevaluativo_set.filter(dependiente=True, status=True)

    def cantidad_campos(self):
        return self.detallemodeloevaluativo_set.values("id").filter(status=True).count()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(ModeloEvaluativo, self).save(*args, **kwargs)


class DetalleModeloEvaluativo(ModeloBase):
    modelo = models.ForeignKey(ModeloEvaluativo, verbose_name=u"Modelo", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=10, verbose_name=u"Nombre campo")
    notaminima = models.FloatField(default=0, verbose_name=u'Nota minima')
    notamaxima = models.FloatField(default=0, verbose_name=u'Nota maxima')
    decimales = models.IntegerField(default=0, verbose_name=u'lugares decimales')
    determinaestadofinal = models.BooleanField(default=False, verbose_name=u"Determina estado final")
    dependiente = models.BooleanField(default=False, verbose_name=u"Campo dependiente")
    dependeasistencia = models.BooleanField(default=False, verbose_name=u"Depende de asistencia")
    orden = models.IntegerField(default=0, verbose_name=u"Orden en acta")
    migrarmoodle = models.BooleanField(default=False, verbose_name=u"Migrar moodle")

    def __str__(self):
        return u'%s (%s a %s)' % (self.nombre, self.notaminima.__str__(), self.notamaxima.__str__())

    class Meta:
        verbose_name = u"Modelo evaluativo - Detalle "
        verbose_name_plural = u"Modelos evaluativos - Detalles"
        ordering = ['orden']
        unique_together = ('modelo', 'nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(DetalleModeloEvaluativo, self).save(*args, **kwargs)

    def en_uso(self):
        return self.evaluaciongenerica_set.filter(status=True).exists()


class Curso(ModeloBase):
    nombre = models.TextField(verbose_name=u"Nombre de Curso")
    codigo = models.TextField(verbose_name=u"Código del Curso", blank=True, null=True)
    fecha_inicio = models.DateField(verbose_name=u'Fecha apertura de Curso')
    fecha_fin = models.DateField(verbose_name=u'Fecha cierre de Curso')
    modeloevaluativo = models.ForeignKey(ModeloEvaluativo, on_delete=models.CASCADE, verbose_name=u"Modelo evaluativo",
                                         null=True, blank=True)
    # min_aprueba_nota = models.IntegerField(verbose_name=u"Minimo aprueba notas")
    # min_aprueba_asistencia = models.IntegerField(verbose_name=u"Minimo aprueba asistencia")
    horas = models.IntegerField(verbose_name=u"Horas del Curso")
    creditos = models.IntegerField(verbose_name=u"Creditos del Curso")
    urlmoodle = models.CharField(default='https://aulaposgrado.unemi.edu.ec/', max_length=500, verbose_name=u'url moodle',
                                 blank=True, null=True)
    keymoodle = models.CharField(default='65293afed416ee1dc5dd1b137c35f03d', max_length=500, verbose_name=u'key moodle',
                                 blank=True, null=True)
    enlacereuniondocente = models.TextField(verbose_name=u"Enlace de Zoom Docente", blank=True, null=True)
    enlacegrabacion = models.TextField(verbose_name=u"Enlace grabaciones", blank=True, null=True)
    enlacepresentacioncurso = models.TextField(verbose_name=u"Enlace presentación del curso", blank=True, null=True)
    idcursomoodle = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'id de curso de moodle')
    cerrado = models.BooleanField(default=False, verbose_name=u'Cerrada', blank=True, null=True)

    def __str__(self):
        return u'%s - %s - %s' % (self.nombre, self.fecha_inicio, self.fecha_fin)

    class Meta:
        verbose_name = u"Curso"
        verbose_name_plural = u"Cursos"
        unique_together = ('codigo',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(Curso, self).save(*args, **kwargs)

    def en_uso(self):
        return self.inscripcioncurso_set.filter(status=True).exists()

    def contar_inscritos(self):
        return self.inscripcioncurso_set.filter(status=True).count()

    def contar_asignaturas(self):
        return self.asignaturacurso_set.filter(status=True).count()

    def inscritos(self):
        return self.inscripcioncurso_set.filter(status=True)

    def categorias_moodle_curso(self):
        cursor = connections['moodle_pos'].cursor()
        sql = """select DISTINCT upper(gc.fullname),it.sortorder  from mooc_grade_grades nota 
                 inner join mooc_grade_items it on nota.itemid=it.id and courseid=%s and itemtype='category' 
                 inner join mooc_grade_categories gc on gc.courseid=it.courseid and gc.id=it.iteminstance and gc.depth=2 
                 where not upper(gc.fullname)='RE'
                 order by it.sortorder ;
                """ % str(self.idcursomoodle)
        cursor.execute(sql)
        results = cursor.fetchall()
        return results

    def notas_de_moodle(self, persona):
        sql = """ SELECT ROUND(nota.finalgrade,2), UPPER(gc.fullname)
                                FROM mooc_grade_grades nota
                        INNER JOIN mooc_grade_items it ON nota.itemid=it.id AND courseid=%s AND itemtype='category'
                        INNER JOIN mooc_grade_categories gc ON gc.courseid=it.courseid AND gc.id=it.iteminstance AND gc.depth=2
                        INNER JOIN mooc_user us ON nota.userid=us.id
                        WHERE us.username ='%s' and not UPPER(gc.fullname)='RE'
                        ORDER BY it.sortorder
                        """ % (str(self.idcursomoodle), persona.usuario.username)

        cursor = connections['moodle_pos'].cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        return results

    def crear_actualizar_categoria_notas_curso_ofimatica(self):
        from django.db import connections
        cursor = None
        cursor = connections['moodle_pos'].cursor()

        #################################################################################################################
        # AGREGAR SISTEMA DE CALIFICACION
        #################################################################################################################
        if self.idcursomoodle:
            cursoid = self.idcursomoodle
            modelonotas = self.modeloevaluativo.detallemodeloevaluativo_set.filter(status=True, migrarmoodle=True)
            if modelonotas:
                query = u"SELECT id FROM mooc_grade_categories WHERE parent is null and depth=1 and courseid= %s" % cursoid
                cursor.execute(query)
                row = cursor.fetchall()
                padrenota = 0
                fecha = int(time.mktime(datetime.now().date().timetuple()))
                if not row:
                    query = u"INSERT INTO mooc_grade_categories(courseid, parent, depth, path, fullname, aggregation, keephigh, droplow, aggregateonlygraded, hidden, timecreated, timemodified) VALUES (%s, null, 1, E'', E'?', 13, 0, 0, 0, 0, %s, %s)" % (
                        cursoid, fecha, fecha)
                    cursor.execute(query)
                    query = u"SELECT id FROM mooc_grade_categories WHERE parent is null and depth=1 and courseid= %s" % cursoid
                    cursor.execute(query)
                    row = cursor.fetchall()
                    query = u"UPDATE mooc_grade_categories SET path='/%s/' WHERE id= %s" % (row[0][0], row[0][0])
                    cursor.execute(query)
                    padrenota = row[0][0]
                else:
                    padrenota = row[0][0]
                if padrenota > 0:
                    ordennota = 1
                    query = u"SELECT id FROM mooc_grade_items WHERE courseid=%s and itemtype='course' and iteminstance=%s" % (
                        cursoid, padrenota)
                    cursor.execute(query)
                    row = cursor.fetchall()
                    if not row:
                        query = u"INSERT INTO mooc_grade_items (courseid, categoryid, itemname, itemtype, itemmodule, iteminstance, itemnumber, iteminfo, idnumber, calculation, gradetype, grademax, grademin, scaleid, outcomeid, gradepass, multfactor, plusfactor, aggregationcoef, aggregationcoef2, sortorder, display, decimals, hidden, locked, locktime, needsupdate, weightoverride, timecreated, timemodified) VALUES (%s, null, null, E'course', null, %s, null, null, null, null, 1, 100, 0, null, null, 0, 1, 0, 0, 0, %s, 0, 2, 0, 0, 0, 0, 0, %s, %s)" % (
                            cursoid, padrenota, ordennota, fecha, fecha)
                        cursor.execute(query)

                    for modelo in modelonotas:
                        query = u"SELECT id FROM mooc_grade_categories WHERE parent=%s and depth=2 and courseid= %s and fullname='%s'" % (
                            padrenota, cursoid, modelo.nombre)
                        cursor.execute(query)
                        row = cursor.fetchall()
                        padremodelo = 0
                        if not row:
                            query = u"INSERT INTO mooc_grade_categories(courseid, parent, depth, path, fullname, aggregation, keephigh, droplow, aggregateonlygraded, hidden, timecreated, timemodified) VALUES (%s, %s, 2, E'', E'%s', 0, 0, 0, 0, 0, %s, %s)" % (
                                cursoid, padrenota, modelo.nombre, fecha, fecha)
                            cursor.execute(query)
                            query = u"SELECT id FROM mooc_grade_categories WHERE parent=%s and depth=2 and courseid= %s and fullname='%s'" % (
                                padrenota, cursoid, modelo.nombre)
                            cursor.execute(query)
                            row = cursor.fetchall()
                            padremodelo = row[0][0]
                            query = u"UPDATE mooc_grade_categories SET path='/%s/%s/' WHERE id= %s" % (
                                padrenota, padremodelo, padremodelo)
                            cursor.execute(query)
                        else:
                            padremodelo = row[0][0]
                        if padremodelo > 0:
                            ordennota += 1
                            query = u"SELECT id FROM mooc_grade_items WHERE courseid=%s and itemtype='category' and iteminstance=%s" % (
                                cursoid, padremodelo)
                            cursor.execute(query)
                            row = cursor.fetchall()
                            if not row:
                                query = u"INSERT INTO mooc_grade_items (courseid, categoryid, itemname, itemtype, itemmodule, iteminstance, itemnumber, iteminfo, idnumber, calculation, gradetype, grademax, grademin, scaleid, outcomeid, gradepass, multfactor, plusfactor, aggregationcoef, aggregationcoef2, sortorder, display, decimals, hidden, locked, locktime, needsupdate, weightoverride, timecreated, timemodified) " \
                                        u"VALUES (%s, null, E'', E'category', null, %s, null, E'', E'', null, 1, %s, 0, null, null, 0, 1, 0, 0, %s, %s, 0, %s, 0, 0, 0, 0, 0, %s, %s)" \
                                        % (cursoid, padremodelo, modelo.notamaxima,
                                           null_to_decimal(modelo.notamaxima / 100, 2), ordennota, 0,
                                           fecha, fecha)
                                cursor.execute(query)

    def crear_actualizar_secciones_curso_ofimatica(self):
        from sga.templatetags.sga_extras import encrypt
        sumary = ''
        from django.db import connections
        cursor = connections['moodle_pos'].cursor()
        #################################################################################################################
        # AGREGAR SILABO
        #################################################################################################################
        if self.idcursomoodle:
            name = u'Datos Generales'
            # sumary += '<iframe src="https://aulagrado.unemi.edu.ec/silabo/versionhtml.php?codisakai=' + self.id.__str__() + '"  class="filter_hvp" id="hvp_4383" style="width:100%; height:1000px; border:0;" frameborder="0" allowfullscreen="allowfullscreen"></iframe>'
            sumary += '<p dir="ltr" style="text-align: left;"></p><h3 style="text-align: center;"><strong><strong><img src="https://lh6.googleusercontent.com/8GmCrCVqKwKXtR0bq-4mnqOdweGpoaTSuQXkCI6SFTqZ4dmVPSRSy_BGplW68bkcnWtd5CHRIgbKPqMrSDiN8nsYnFObQyE56H7hotHeqfrpXUOLSq2HdV4ZP6Ah1IbWYEzPOrIQk6p9-gpr_1M2"></strong><br></strong>'\
                        +'</h3><h3><strong>Datos generales del curso:&nbsp;&nbsp;</strong><br></h3><div><div><p dir="ltr"><a href="' + self.enlacepresentacioncurso + '" target="_blank">' + self.enlacepresentacioncurso + '</a><br></p>'\
                        + '<p dir="ltr"><strong><br></strong></p><p dir="ltr"><strong>Enlace permanente a las sesiones de Zoom:</strong></p><p dir="ltr"><a href="'+ self.enlacereuniondocente +'" target="_blank">' + self.enlacereuniondocente + '</a></p>'\
                        +    '<p dir="ltr"><strong>Grabaciones:&nbsp;</strong></p><p dir="ltr"><span>' + self.enlacegrabacion + '<br></span></p></div></div>'

            # sumary = remover_comilla_simple(sumary)
            query = """UPDATE mooc_course_sections SET name = '%s', summary='%s', availability='%s'  WHERE course = %s and section = %s """ % (
                name, sumary, '{"op":"&","c":[],"showc":[]}', self.idcursomoodle, 0)
            cursor.execute(query)
            #
            #  query = """ UPDATE mooc_course_sections SET name = 'Unidad 1: Word', summary=' '  WHERE course = %s and section = 1 """ % (
            #      self.idcursomoodle)
            #  cursor.execute(query)
            #
            #  query = """ UPDATE mooc_course_sections SET name = 'Unidad 2: Excel' , summary='' WHERE course = %s and section = 2 """ % (
            #      self.idcursomoodle)
            #  cursor.execute(query)
            #
            #  query = """ UPDATE mooc_course_sections SET name = 'Unidad 3: Power Point' , summary='' WHERE course = %s and section = 3 """ % (
            #      self.idcursomoodle)
            #  cursor.execute(query)
            #  # validar si ya estan creados que actualice el nombre

            sql = """select * from mooc_course_sections WHERE course = %s and section = 1 """ % (self.idcursomoodle)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if buscar:
                instanceid = buscar[0][0]
                query = """ UPDATE mooc_course_sections SET name = 'Unidad 1: Word' , summary='' WHERE course = %s and section = 1 """ % (
                    self.idcursomoodle)
            else:
                query = """ INSERT INTO mooc_course_sections (id, course, section, name, summary, summaryformat, visible, timemodified) VALUES (default, %s, 1, E'Unidad 1: Word', E'', 1, 1, 55454545454)    """ % (
                    self.idcursomoodle)
            cursor.execute(query)

            sql = """select * from mooc_course_sections WHERE course = %s and section = 2 """ % (self.idcursomoodle)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if buscar:
                instanceid = buscar[0][0]
                query = """ UPDATE mooc_course_sections SET name = 'Unidad 2: Excel' , summary='' WHERE course = %s and section = 2 """ % (
                    self.idcursomoodle)
            else:
                query = """ INSERT INTO mooc_course_sections (id, course, section, name, summary, summaryformat, visible, timemodified) VALUES (default, %s, 2, E'Unidad 2: Excel', E'', 1, 1, 55454545454)    """ % (
                    self.idcursomoodle)
            cursor.execute(query)

            sql = """select * from mooc_course_sections WHERE course = %s and section = 3 """ % (self.idcursomoodle)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if buscar:
                instanceid = buscar[0][0]
                query = """ UPDATE mooc_course_sections SET name = 'Unidad 3: Power Point' , summary='' WHERE course = %s and section = 3 """ % (
                    self.idcursomoodle)
            else:
                query = """ INSERT INTO mooc_course_sections (id, course, section, name, summary, summaryformat, visible, timemodified) VALUES (default, %s, 3, E'Unidad 3: Power Point', E'', 1, 1, 55454545454)    """ % (
                    self.idcursomoodle)
            cursor.execute(query)

            # sql = """select * from mooc_course_sections WHERE course = %s and section = 4 """ % (self.idcursomoodle)
            # cursor.execute(sql)
            # buscar = cursor.fetchall()
            # if buscar:
            #     instanceid = buscar[0][0]
            #     query = """ UPDATE mooc_course_sections SET name = 'Actividades contacto con el docente' , summary='' WHERE course = %s and section = 4 """ % (
            #         self.idcursomoodle)
            # else:
            #     query = """ INSERT INTO mooc_course_sections (id, course, section, name, summary, summaryformat, visible, timemodified) VALUES (default, %s, 4, E'Actividades contacto con el docente', E'', 1, 1, 55454545454)    """ % (
            #         self.idcursomoodle)
            # cursor.execute(query)

            fecha = int(time.mktime(datetime.now().timetuple()))
            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (
            fecha, self.idcursomoodle)
            cursor.execute(query)


    def crear_actualizar_curso_ofimatica(self):
        from moodle import moodle
        AGREGAR_MODELO_NOTAS = True
        AGREGAR_SECCIONES = True
        AGREGAR_DOCENTE = True
        try:
            curso_ofimatica = self
            if self.modeloevaluativo:
                # programa_maestria = grupo_titulacion_posgrado.configuracion
                # periodo = grupo_titulacion_posgrado.configuracion.periodo
                # ----------------------------------------------------------------------------------------------------------------
                parent_grupoid = 0
                tipourl = 1
                parent_grupoid = 4231  # categoria de moodle creada EXÁMEN DE CARACTER COMPLEXIVO TITULACIÓN
                # ano = '%s_%s-%s_%s' % (periodo.inicio.year, periodo.inicio.month, periodo.fin.year, periodo.fin.month)
                # importar moodle
                # ----------------------------------------------------------------------------------------------------------------
                # ----------------------------------------------------------------------------------------------------------------
                # BUSCANDO LA CATEGORIA PADRE
                bgrupo = moodle.BuscarCategoriasid(self, tipourl, parent_grupoid)
                if bgrupo:
                    if 'id' in bgrupo[0]:
                        parent_grupoid = bgrupo[0]['id']
                contador = 0
                # idnumber_periodo = u'PERIO_PK_%s-%s_POSG' % (periodo.id, ano)
                print(bgrupo)
                if parent_grupoid > 0:

                    """"
                        CREANDO LOS CURSOS
                    """
                    # idnumber_curso = grupo_titulacion_posgrado.obtener_codigo_grupo()
                    idnumber_curso = u'%s_OFIMÁTICA_GRUPO_%s_%s' % (self.fecha_fin.year, self.pk, self.codigo)
                    buscar_curso = moodle.BuscarCursos(self, tipourl, 'idnumber', idnumber_curso)
                    if not buscar_curso:
                        buscar_curso = moodle.BuscarCursos(self, tipourl, 'idnumber',
                                                           idnumber_curso)
                    parent_cursoid = 0
                    if buscar_curso['courses']:
                        if 'id' in buscar_curso['courses'][0]:
                            parent_cursoid = buscar_curso['courses'][0]['id']
                    else:
                        numsections = 3
                        summary = u'%s\n\nEnlace Presentación del Curso:\n\n%s\n\nEnlace reuniones con docente:\n\n%s\n\nEnlace grabaciones del curso:<br>%s' % (
                        self.nombre, self.enlacepresentacioncurso, self.enlacereuniondocente, self.enlacegrabacion)
                        startdate = int(time.mktime(curso_ofimatica.fecha_inicio.timetuple()))
                        enddate = int(time.mktime(curso_ofimatica.fecha_fin.timetuple()))
                        buscar_curso = moodle.CrearCursos(self, tipourl,
                                                             u'CURSO OFIMÁTICA: %s' % curso_ofimatica,
                                                             curso_ofimatica,
                                                             parent_grupoid,
                                                             idnumber_curso, summary, startdate,
                                                             enddate, numsections)
                        print(buscar_curso)
                        parent_cursoid = buscar_curso[0]['id']

                    if parent_cursoid > 0:
                        if curso_ofimatica.idcursomoodle != parent_cursoid:
                            curso_ofimatica.idcursomoodle = parent_cursoid
                            curso_ofimatica.save()

                    if AGREGAR_MODELO_NOTAS:
                        try:
                            curso_ofimatica.crear_actualizar_categoria_notas_curso_ofimatica()
                        except Exception:
                            print("Error al exportar el modelo evaluativo")

                    if AGREGAR_SECCIONES:
                        try:
                            curso_ofimatica.crear_actualizar_secciones_curso_ofimatica()
                        except Exception:
                            print("Error al exportar las secciones del curso")

                    # if AGREGAR_DOCENTE:
                    #     try:
                    #         grupo_titulacion_posgrado.crear_actualizar_tutor_curso_grupo_titulacion_posgrado(
                    #             moodle, tipourl)
                    #     except Exception:
                    #         print("Error al exportar el modelo evaluativo")
        except Exception as ex:
            pass


    def crear_actualizar_estudiantes_curso_ofimatica(self, moodle, tipourl):
        #################################################################################################################
        # AGREGAR ESTUDIANTE
        #################################################################################################################
        from sga.funciones import log
        from Moodle_Funciones import buscarUsuario
        cursor = None
        cursor = connections['moodle_pos'].cursor()
        if self.idcursomoodle and cursor:
            cursoid = self.idcursomoodle
            contador = 0
            rolestudiante = 5
            for estudiante in self.inscripcioncurso_set.filter(status=True):
                try:
                    contador += 1
                    bandera = 0
                    persona = estudiante.inscripcion.persona if estudiante.inscripcion else estudiante.persona
                    print("Verificando si esta enrolado: %s" % persona)
                    username = persona.usuario.username
                    queryest = """ SELECT DISTINCT asi.userid 
                                            FROM  mooc_role_assignments asi 
                                            INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID 
                                            INNER JOIN mooc_user usr2 ON usr2.id=asi.userid AND ASI.ROLEID=%s AND CON.INSTANCEID=%s AND usr2.username='%s'
                                                        """ % (rolestudiante, cursoid, username)

                    cursor.execute(queryest)
                    estudianteid = None
                    rowest = cursor.fetchall()
                    if not rowest:
                        print("No esta matriculado, procediendo a enrolar: %s" % persona)
                        username = persona.usuario.username
                        estudianteid = buscarUsuario(username, cursor)
                        if estudianteid is None:
                            idnumber_user = persona.identificacion()
                            bandera = 1
                            bestudiante = moodle.CrearUsuario(self, tipourl,
                                                              u'%s' % persona.usuario.username,
                                                              u'%s' % persona.identificacion(),
                                                              u'%s' % persona.nombres,
                                                              u'%s %s' % (persona.apellido1, persona.apellido2),
                                                              u'%s' % persona.email if persona.email else persona.emailinst,
                                                              idnumber_user,
                                                              u'MILAGRO',
                                                              u'ECUADOR')
                            estudianteid = bestudiante[0]['id']
                        if bandera == 0:
                            lastname = str(persona.apellido1) + ' ' + str(persona.apellido2)
                            sql = f"UPDATE mooc_user SET idnumber ='{persona.identificacion()}'," \
                                  f" firstname='{persona.nombres}', lastname='{lastname}', email='{persona.emailinst}' where username='{persona.usuario.username}' "
                            cursor.execute(sql)
                        if estudianteid > 0:
                            rolest = moodle.EnrolarCurso(self, tipourl,
                                                         5,
                                                         estudianteid, cursoid)
                            if persona.idusermoodleposgrado != estudianteid:
                                persona.idusermoodleposgrado = estudianteid
                                persona.save()
                        print('************Estudiante: %s *** %s idm: %s rol: %s est: %s' % (
                            contador, persona, self.idcursomoodle, rolest, estudianteid))

                except Exception as ex:
                    log(u'Moodle Error al crear Estudiante: %s %s (%s)' % (persona, estudiante, estudiante.id), None,
                        "add", User.objects.get(pk=1))
                    print('Error al crear estudiante %s' % ex)

            # self.quitar_estudiantes_curso_ofimatica(moodle, tipourl)


    def quitar_estudiantes_curso_ofimatica(self, moodle, tipourl):
        from django.db import connections
        cursor = connections['moodle_pos'].cursor()
        #################################################################################################################
        # QUITAR ESTUDIANTE
        #################################################################################################################
        if self.idcursomoodle:
            cursoid = self.idcursomoodle
            idestudiantes = ""
            for x in self.inscripcioncurso_set.filter(status=True).values_list(
                    'inscripcion__persona__idusermoodleposgrado'):
                idestudiantes += "%s," % x[0]
            # profesor = self.tutor
            # if profesor and profesor.persona.usuario and not 'POR DEFINIR' in profesor.persona.nombres:
            #     idestudiantes += "%s," % profesor.persona.idusermoodleposgrado
            queryest = """
                              SELECT DISTINCT asi.userid, asi.roleid
                              FROM  mooc_role_assignments asi
                              INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID AND ASI.ROLEID=%s AND CON.INSTANCEID=%s AND asi.userid not in(%s0)
                      """ % (5, cursoid, idestudiantes)
            cursor.execute(queryest)
            rowest = cursor.fetchall()
            if rowest:
                for deluserest in rowest:
                    unrolest = moodle.UnEnrolarCurso(self, tipourl, deluserest[1], deluserest[0],
                                                     cursoid)
                    print('************ Eliminar Estudiante: *** %s' % deluserest[0])


class InscripcionCurso(ModeloBase):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, verbose_name=u"Curso")
    inscripcion = models.ForeignKey("sga.Inscripcion",blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Inscripcion")
    persona = models.ForeignKey("sga.Persona", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona")
    correo = models.CharField(verbose_name=u"Correo Electronico", max_length=255)
    archivocertificado = models.FileField(upload_to='oma/epunemi/certificado', blank=True, null=True,
                                          verbose_name=u'Archivo Certicado pdf')

    class Meta:
        verbose_name = u"Inscripción Curso"
        verbose_name_plural = u"Inscripciónes Curso"

    def delete_inscripcion(self):
        if self.asignaturainscripcioncurso_set.filter(status=True).exists():
            for aux in self.asignaturainscripcioncurso_set.filter(status=True):
                aux.evaluaciongenerica_set.filter(status=True).update(status=False)
                aux.status = False
                aux.save()

    # Elimina las evaluaciones genericas de los inscritos cuando cambia el modelo evaluativo del curso
    def edit_modelo_curso(self):
        if self.asignaturainscripcioncurso_set.filter(status=True).exists():
            for aux in self.asignaturainscripcioncurso_set.filter(status=True):
                aux.evaluaciongenerica_set.filter(status=True).update(status=False)
        # aux = self.asignaturainscripcioncurso_set.filter(status=True).first()
        # aux.evaluaciongenerica_set.filter(status=True).update(status=False)

    def lista_emails_envio_oma(self):
        lista = []
        if self.correo:
            lista.append(self.correo)
        if self.persona.email:
            lista.append(self.persona.email)
        elif self.inscripcion.persona.email:
            lista.append(self.inscripcion.persona.email)
        if self.persona.emailinst:
            lista.append(self.persona.emailinst)
        elif self.inscripcion.persona.emailinst:
            lista.append(self.persona.emailinst)
        return lista

    def esta_aprobado(self):
        if self.asignaturainscripcioncurso_set.filter(status=True, estado=2).exists():
            return 2 #REPROBADO
        elif self.asignaturainscripcioncurso_set.filter(status=True, estado=0).exists():
            return 0 #PENDIENTE
        else:
            return 1 #APROBADO

    def mis_asignaturas(self):
        asignaturas_todas= self.asignaturainscripcioncurso_set.filter(status=True)
        if asignaturas_todas.exists():
            asignatura= asignaturas_todas.first()
            return asignatura
        return None


    def asignaturas(self):
        return self.asignaturainscripcioncurso_set.filter(status=True)

class AsignaturaCurso(ModeloBase):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, verbose_name=u"Curso")
    asignatura = models.ForeignKey("sga.Asignatura", on_delete=models.CASCADE, verbose_name=u"Asignatura")

    class Meta:
        verbose_name = u"Asignatura Curso"
        verbose_name_plural = u"Asignaturas Curso"


class AsignaturaInscripcionCurso(ModeloBase):
    inscripcioncurso = models.ForeignKey(InscripcionCurso, on_delete=models.CASCADE, verbose_name=u"inscripción Curso")
    asignaturacurso = models.ForeignKey(AsignaturaCurso, on_delete=models.CASCADE, verbose_name=u"Asignatura Curso")
    estado = models.IntegerField(choices=ESTADOS_ASIGNATURA_INSCRIPCION_CURSO, verbose_name=u"Estado", default=0)
    nota = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Nota")
    asistencia = models.IntegerField(default=0, verbose_name=u'Asistencia')

    class Meta:
        verbose_name = u"Asignatura Curso"
        verbose_name_plural = u"Asignaturas Curso"

    def __str__(self):
        return u'%s - %s - %s' % (self.inscripcioncurso.inscripcion.persona.nombre_completo(), self.inscripcioncurso.curso.nombre, self.asignaturacurso.asignatura)

    def evaluacion_generica(self):
        if not self.evaluaciongenerica_set.values("id").filter(status=True).exists():
            modelo = self.asignaturacurso.curso.modeloevaluativo
            for campos in modelo.detallemodeloevaluativo_set.filter(status=True):
                evaluacion = EvaluacionGenerica(asignaturainscripcion=self,
                                                detallemodeloevaluativo=campos,
                                                valor=0)
                evaluacion.save()
        return self.evaluaciongenerica_set.filter(status=True)

    def campo(self, campo):
        if self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo).exists():
            return self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo)[0]
        return None

    def actualiza_estado(self):
        self.estado = 0 #PENDIENTE
        if self.nota > 0:
            if self.nota >= self.inscripcioncurso.curso.modeloevaluativo.notaaprobar:
                self.estado = 1 #APROBADO
            else:
                self.estado = 2 #REPROBADO
        if self.inscripcioncurso.curso.cerrado and self.nota < self.inscripcioncurso.curso.modeloevaluativo.notaaprobar:
            self.estado = 2 #REPROBADO
        self.save()

    def verifica_evaluacion_generica(self):
        if not self.evaluaciongenerica_set.filter(status=True).exists():
            modelo = self.inscripcioncurso.curso.modeloevaluativo
            for campos in modelo.detallemodeloevaluativo_set.filter(status=True):
                evaluacion = EvaluacionGenerica(asignaturainscripcion=self,
                                                detallemodeloevaluativo=campos,
                                                valor=0)
                evaluacion.save()
        return True

    def valor_nombre_campo(self, campo):
        if self.verifica_evaluacion_generica():
            if self.evaluaciongenerica_set.values("valor").filter(status=True, detallemodeloevaluativo__nombre=campo):
                return self.evaluaciongenerica_set.values("valor").filter(status=True, detallemodeloevaluativo__nombre=campo)[
                    0].get("valor")
            return 0
        return 0

    def cierre_materia_asignada(self):
        if self.estado==1:
            creditos = self.inscripcioncurso.curso.creditos
            horas = self.inscripcioncurso.curso.horas
            inscripcioncurso=self.inscripcioncurso
            existente = None
            existente=HistoricoRecordAcademico.objects.filter(status=True,
                                                                 inscripcion=self.inscripcioncurso.inscripcion,
                                                                 asignatura=self.asignaturacurso.asignatura)
            if existente.values("id").exists():
                existente_ofimatica = existente.filter(ofimatica=inscripcioncurso).last()
                if existente_ofimatica:
                    existente_ofimatica.nota = self.nota
                    existente_ofimatica.modulomalla = None
                    existente_ofimatica.asignaturamalla = None
                    existente_ofimatica.horas = horas
                    existente_ofimatica.creditos = creditos
                    existente_ofimatica.valida = True
                    existente_ofimatica.validapromedio = False
                    existente_ofimatica.asistencia = 100
                    existente_ofimatica.sinasistencia = False
                    existente_ofimatica.fecha = datetime.now().date()
                    existente_ofimatica.convalidacion = False
                    existente_ofimatica.homologada = True
                    existente_ofimatica.aprobada = True
                    existente_ofimatica.materiaregular = None
                    existente_ofimatica.pendiente = False
                    existente_ofimatica.completonota = False
                    existente_ofimatica.completoasistencia = False
                    existente_ofimatica.ofimatica=inscripcioncurso
                    existente_ofimatica.observaciones=f'VALIDADO CURSO {inscripcioncurso.curso} - EPUNEMI'
                    existente_ofimatica.save()
                    existente_ofimatica.actualizar()
                else:
                    existente=existente.filter(aprobada=True).last()
                    if not existente:
                        historico = HistoricoRecordAcademico(inscripcion=self.inscripcioncurso.inscripcion,
                                                             asignatura=self.asignaturacurso.asignatura,
                                                             modulomalla=None,
                                                             asignaturamalla=None,
                                                             nota=self.nota,
                                                             creditos=creditos,
                                                             horas=horas,
                                                             valida=True,
                                                             validapromedio=False,
                                                             asistencia=self.asistencia,
                                                             sinasistencia=False,
                                                             completonota=False,
                                                             completoasistencia=False,
                                                             fecha=datetime.now().date(),
                                                             convalidacion=False,
                                                             homologada=True,
                                                             aprobada=True,
                                                             pendiente=False,
                                                             materiaregular=None,
                                                             ofimatica=inscripcioncurso,
                                                             observaciones='VALIDADO CURSO %s - EPUNEMI' % self.inscripcioncurso.curso)
                        historico.save()
                        if self.inscripcioncurso.inscripcion.recordacademico_set.values("id").filter(status=True,
                                                                                                     asignatura=historico.asignatura).exists():
                            historico.recordacademico = self.inscripcioncurso.inscripcion.recordacademico_set.filter(status=True,
                                                                                         asignatura=historico.asignatura)[0]
                            historico.save()
                        historico.actualizar()
            else:
                historico = HistoricoRecordAcademico(inscripcion=self.inscripcioncurso.inscripcion,
                                                     asignatura=self.asignaturacurso.asignatura,
                                                     modulomalla=None,
                                                     asignaturamalla=None,
                                                     nota=self.nota,
                                                     creditos=creditos,
                                                     horas=horas,
                                                     valida=True,
                                                     validapromedio=False,
                                                     asistencia=self.asistencia,
                                                     sinasistencia=False,
                                                     completonota=False,
                                                     completoasistencia=False,
                                                     fecha=datetime.now().date(),
                                                     convalidacion=False,
                                                     homologada=True,
                                                     aprobada=True,
                                                     pendiente=False,
                                                     materiaregular=None,
                                                     ofimatica=inscripcioncurso,
                                                     observaciones='VALIDADO CURSO %s - EPUNEMI' % self.inscripcioncurso.curso)
                historico.save()
                if self.inscripcioncurso.inscripcion.recordacademico_set.values("id").filter(status=True, asignatura=historico.asignatura).exists():
                    historico.recordacademico = self.inscripcioncurso.inscripcion.recordacademico_set.filter(status=True, asignatura=historico.asignatura)[0]
                    historico.save()
                historico.actualizar()

class EvaluacionGenerica(ModeloBase):
    asignaturainscripcion = models.ForeignKey(AsignaturaInscripcionCurso,blank=True, null=True, on_delete=models.CASCADE,
                                              verbose_name=u"Asignatura Inscripción Curso")
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativo, on_delete=models.CASCADE,
                                                verbose_name=u"Detalle Modelo Evaluativo")
    valor = models.FloatField(default=0, verbose_name=u'Valor evaluación')
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha modificación')
    inscripcioncurso = models.ForeignKey(InscripcionCurso, on_delete=models.CASCADE,blank=True, null=True, verbose_name=u"inscripción Curso")
    class Meta:
        verbose_name = u"Evaluación Genérica"
        verbose_name_plural = u"Evaluaciones Genéricas"


    def save(self, *args, **kwargs):
        if self.valor >= self.detallemodeloevaluativo.notamaxima:
            self.valor = self.detallemodeloevaluativo.notamaxima
        elif self.valor <= self.detallemodeloevaluativo.notaminima:
            self.valor = self.detallemodeloevaluativo.notaminima
        self.valor = null_to_decimal(self.valor, self.detallemodeloevaluativo.decimales)
        super(EvaluacionGenerica, self).save(*args, **kwargs)

class AuditoriaNotasOma(ModeloBase):
    evaluaciongenerica = models.ForeignKey(EvaluacionGenerica, verbose_name=u'Planificación materia',
                                           on_delete=models.CASCADE)
    manual = models.BooleanField(default=False, verbose_name=u'Agregado manualmente')
    calificacion = models.FloatField(default=0, verbose_name=u'Calificación')
    observacion = models.TextField(blank=True, null=True, verbose_name=u'Observacion')

    class Meta:
        verbose_name = u"Auditoria de nota"
        verbose_name_plural = u"Auditoria de notas"