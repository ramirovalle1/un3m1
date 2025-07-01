from requests import get, post

# Module variables to connect to moodle api
# URL = "http://virtual.unemi.edu.ec"

# KEY = '28ce103f0d08a13c3233e60772d17235'
from settings import DEBUG

ENDPOINT = "/webservice/rest/server.php"


def rest_api_parameters(in_args, prefix='', out_dict=None):
    if out_dict == None:
        out_dict = {}
    if not type(in_args) in (list, dict):
        out_dict[prefix] = in_args
        return out_dict
    if prefix == '':
        prefix = prefix + '{0}'
    else:
        prefix = prefix + '[{0}]'
    if type(in_args) == list:
        for idx, item in enumerate(in_args):
            rest_api_parameters(item, prefix.format(idx), out_dict)
    elif type(in_args) == dict:
        for key, item in in_args.items():
            rest_api_parameters(item, prefix.format(key), out_dict)
    return out_dict


def call(fname, periodo, tipourl, **kwargs):
    try:
        if tipourl == 1:
            URL = periodo.urlmoodle  #"http://aulagradoa.unemi.edu.ec"
            KEY = periodo.keymoodle  #'f3202c47266fe29f2f604eca8ece6baf'
        elif tipourl == 2:
            URL = periodo.urlmoodle2  # "http://aulanivelacion.unemi.edu.ec"
            KEY = periodo.keymoodle2  # 'f3202c47266fe29f2f604eca8ece6baf'

        else:
            URL = periodo.urlmoodleenlinea  # "http://aulagradob.unemi.edu.ec"
            KEY = periodo.keymoodleenlinea  # 'f3202c47266fe29f2f604eca8ece6baf'

        """
            ESTO FUNCIONA SI ESTAMOS LOCAL, EN PRODUCCIÓN TOMARÍA LA VALIDACIÓN ANTERIOR
            EN CASO DE REQUERIR CAMBIAR LA URL DEL ACCESO A LA API REST DE MOODLE CONSIDERAR ÚNICAMENTE LOCAL SIN SUBIR
            LOS CAMBIOS AL SERVIDOR
        """
        # if DEBUG:
            # URL = "http://192.168.51.221/moodle"
            # KEY = '65293afed416ee1dc5dd1b137c35f03d'
            # URL = "http://127.0.0.1/moodle"
            # KEY = 'c9b0066a33d74960f244348be839befe'

        parameters = rest_api_parameters(kwargs)
        parameters.update({"wstoken": KEY, 'moodlewsrestformat': 'json', "wsfunction": fname})
        response = post(URL + ENDPOINT, parameters, verify=False)
        respuesta = response.json()
        response.close()
        # print(response.status_code, response.request)
        return respuesta
    except Exception as ex:
        return []


######################################################################################################################3
######################################################################################################################3
# FUNCIONES PRINCIPALES PARA CONFIGURAR CATEGORIAS EN MOODLE
######################################################################################################################3
######################################################################################################################3
def BuscarCategorias(periodo, tipourl, idnumber):
    return call('core_course_get_categories', periodo, tipourl, criteria=[{'key':'idnumber', 'value':idnumber}], addsubcategories=0)


def BuscarCategoriasid(periodo, tipourl, id):
    return call('core_course_get_categories', periodo, tipourl, criteria=[{'key':'id', 'value':id}], addsubcategories=0)


def CrearCategorias(periodo, tipourl, name, idnumber, description, parent=0):
    """
    [categories] =>
    Array
        (
        [0] =>
            Array
                (
                [name] => string //new category name
                [parent] => int valor por defecto para "0" //the parent category id inside which the new category will be created
                [idnumber] => string Opcional //the new category idnumber
                [description] => string Opcional //the new category description
                [descriptionformat] => int Valor por defecto para "1" //description format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                [theme] => string Opcional //the new category theme. This option must be enabled on moodle
                )
        )
    :param categories:
    :return:
    """
    return call('core_course_create_categories', periodo, tipourl, categories=[{'name': u'%s' % name, 'idnumber': idnumber, 'description': description, 'parent': parent}])


######################################################################################################################3
######################################################################################################################3
# FUNCIONES PRINCIPALES PARA CONFIGURAR CURSOS EN MOODLE
######################################################################################################################3
######################################################################################################################3
def BuscarCursos(periodo, tipourl, vfield, vvalue):
    """
    string  Valor por defecto para "" //The field to search can be left empty for all courses or:
                    id: course id
                    ids: comma separated course ids
                    shortname: course short name
                    idnumber: course id number
                    category: category id the course belongs to
    :param vfield:
    :param vvalue:
    :return:
    """
    return call('core_course_get_courses_by_field', periodo, tipourl, field=vfield, value=vvalue)

# def BuscarCursoModulo(periodo, tipourl, codigo):
#     # return call('core_course_get_course_module', periodo, tipourl, field=vfield, value=vvalue)
#     # return call('core_course_get_course_module', periodo, tipourl, criteria=[{'key': 'id', 'value': id}], addsubcategories=0)
#     # return call('core_course_get_course_module', periodo, tipourl, criteria=[{'key': vkey, 'value': vvalue}])
#     return call('core_course_get_course_module', periodo, tipourl, cmid=codigo)

def CrearCursos(periodo, tipourl, fullname, shortname, categoryid , idnumber, summary, startdate, enddate, numsections):
    """
    Estructura general

      //courses to create
    list of (
    object {
        fullname string   //full name
        shortname string   //course short name
        categoryid int   //category id
        idnumber string  Opcional //id number
        summary string  Opcional //summary
        summaryformat int  Valor por defecto para "1" //summary format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
        startdate int  Opcional //timestamp when the course start
        enddate int  Opcional //timestamp when the course end
        numsections  Opcional //(deprecated, use courseformatoptions) number of weeks/topics
        hiddensections int  Opcional //(deprecated, use courseformatoptions) How the hidden sections in the course are displayed to students
        defaultgroupingid int  Valor por defecto para "0" //default grouping id
        enablecompletion int  Opcional //Enabled, control via completion and activity settings. Disabled,
                                                not shown in activity settings.
        completionnotify int  Opcional //1: yes 0: no
        lang string  Opcional //forced course language
        forcetheme string  Opcional //name of the force theme
        courseformatoptions  Opcional //additional options for particular course format
        list of (
            object {
            name string   //course format option name
            value string   //course format option value
            }
        )}
    )
    :param fullname:
    :param shortname:
    :param categoryid:
    :param idnumber:
    :param summary:
    :param startdate:
    :param enddate:
    :return:
    """
    # VARIABLES CON VALORES POR DEFECTO

    maxbytes = 20971520 # Valor por defecto para "0" //largest size of file that can be uploaded into the course
    format = 'topics' # Valor por defecto para "topics" //course format: weeks, topics, social, site,..
    showgrades = 1 # Valor por defecto para "1" //1 if grades are shown, otherwise 0
    newsitems = 5 # Valor por defecto para "5" //number of recent items appearing on the course page

    showreports = 1 # Valor por defecto para "0" //are activity report shown (yes = 1, no =0)
    visible = 1 # Opcional //1: available to student, 0:not available
    groupmode = 0 # Valor por defecto para "0" //no group, separate, visible
    groupmodeforce = 0 # Valor por defecto para "0" //1: yes, 0: no
    return call('core_course_create_courses', periodo, tipourl, courses=[{'fullname': u'%s' % fullname,
                                                        'shortname': shortname,
                                                        'categoryid': categoryid,
                                                        'idnumber': idnumber,
                                                        'summary': summary, 'format': format,
                                                        'showgrades': showgrades,
                                                        'newsitems': newsitems,
                                                        'startdate': startdate,
                                                        'enddate': enddate,
                                                        'numsections': numsections,
                                                        'maxbytes': maxbytes,
                                                        'showreports': showreports,
                                                        'visible': visible,
                                                        'groupmode': groupmode,
                                                        'groupmodeforce': groupmodeforce}])


def CrearCursosTarjeta(periodo, tipourl, fullname, shortname, categoryid , idnumber, summary, startdate, enddate, numsections):
    """
    Estructura general

      //courses to create
    list of (
    object {
        fullname string   //full name
        shortname string   //course short name
        categoryid int   //category id
        idnumber string  Opcional //id number
        summary string  Opcional //summary
        summaryformat int  Valor por defecto para "1" //summary format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
        startdate int  Opcional //timestamp when the course start
        enddate int  Opcional //timestamp when the course end
        numsections  Opcional //(deprecated, use courseformatoptions) number of weeks/topics
        hiddensections int  Opcional //(deprecated, use courseformatoptions) How the hidden sections in the course are displayed to students
        defaultgroupingid int  Valor por defecto para "0" //default grouping id
        enablecompletion int  Opcional //Enabled, control via completion and activity settings. Disabled,
                                                not shown in activity settings.
        completionnotify int  Opcional //1: yes 0: no
        lang string  Opcional //forced course language
        forcetheme string  Opcional //name of the force theme
        courseformatoptions  Opcional //additional options for particular course format
        list of (
            object {
            name string   //course format option name
            value string   //course format option value
            }
        )}
    )
    :param fullname:
    :param shortname:
    :param categoryid:
    :param idnumber:
    :param summary:
    :param startdate:
    :param enddate:
    :return:
    """
    # VARIABLES CON VALORES POR DEFECTO

    maxbytes = 10485760 # Valor por defecto para "0" //largest size of file that can be uploaded into the course
    format = 'remuiformat' # Valor por defecto para "topics" //course format: weeks, topics, social, site,..
    showgrades = 1 # Valor por defecto para "1" //1 if grades are shown, otherwise 0
    newsitems = 5 # Valor por defecto para "5" //number of recent items appearing on the course page

    showreports = 1 # Valor por defecto para "0" //are activity report shown (yes = 1, no =0)
    visible = 1 # Opcional //1: available to student, 0:not available
    groupmode = 0 # Valor por defecto para "0" //no group, separate, visible
    groupmodeforce = 0 # Valor por defecto para "0" //1: yes, 0: no
    return call('core_course_create_courses', periodo, tipourl, courses=[{'fullname': u'%s' % fullname,
                                                        'shortname': shortname,
                                                        'categoryid': categoryid,
                                                        'idnumber': idnumber,
                                                        'summary': summary, 'format': format,
                                                        'showgrades': showgrades,
                                                        'newsitems': newsitems,
                                                        'startdate': startdate,
                                                        'enddate': enddate,
                                                        'numsections': numsections,
                                                        'maxbytes': maxbytes,
                                                        'showreports': showreports,
                                                        'visible': visible,
                                                        'groupmode': groupmode,
                                                        'groupmodeforce': groupmodeforce}])


######################################################################################################################
######################################################################################################################
# FUNCIONES PARA CREAR USUARIO
######################################################################################################################
######################################################################################################################
def BuscarUsuario(periodo, tipourl, vkey, vvalue):
    """
    list of (
        object {
            key string   //the user column to search, expected keys (value format) are:
                        "id" (int) matching user id,
                        "lastname" (string) user last name (Note: you can use % for searching but it may be considerably slower!),
                        "firstname" (string) user first name (Note: you can use % for searching but it may be considerably slower!),
                        "idnumber" (string) matching user idnumber,
                        "username" (string) matching user username,
                        "email" (string) user email (Note: you can use % for searching but it may be considerably slower!),
                        "auth" (string) matching user auth plugin
            value string   //the value to search
        }
    )
    :param vkey:
    :param vvalue:
    :return:
    """
    return call('core_user_get_users', periodo, tipourl, criteria=[{'key': vkey, 'value': vvalue}])


def EnrolarCurso(periodo, tipourl, roleid, userid, courseid):
    """
    Roles definidos
    teacher => 3
    No edit Teacher => 4
    estudent => 5
    list of (
        object {
            roleid int   //Role to assign to the user
            userid int   //The user that is going to be enrolled
            courseid int   //The course to enrol the user role in

            timestart int  Opcional //Timestamp when the enrolment start
            timeend int  Opcional //Timestamp when the enrolment end
            suspend int  Opcional //set to 1 to suspend the enrolment
        }
    )
    :param roleid:
    :param userid:
    :param courseid:
    :return:
    """
    return call('enrol_manual_enrol_users', periodo, tipourl, enrolments=[{'roleid': roleid,
                                                         'userid': userid,
                                                         'courseid': courseid}])


def UnEnrolarCurso(periodo, tipourl, roleid, userid, courseid):
    """
    Roles definidos
    teacher => 3
    No edit Teacher => 4
    estudent => 5
    list of (
        object {
            roleid int   //Role to assign to the user
            userid int   //The user that is going to be enrolled
            courseid int   //The course to enrol the user role in

            timestart int  Opcional //Timestamp when the enrolment start
            timeend int  Opcional //Timestamp when the enrolment end
            suspend int  Opcional //set to 1 to suspend the enrolment
        }
    )
    :param roleid:
    :param userid:
    :param courseid:
    :return:
    """
    return call('enrol_manual_unenrol_users', periodo, tipourl, enrolments=[{'userid': userid,
                                                           'courseid': courseid,
                                                           'roleid': u'%s' % roleid}])


def EliminarUsuario(periodo, tipourl, iduser):
    """
    list of (
    int   //user ID
    )
    :param iduser:
    :return:
    """
    return call('core_user_delete_users', periodo, tipourl, userids=[iduser])


def CrearUsuario(periodo, tipourl, username, password, firstname , lastname, email, idnumber , city, country):
    """
    Estructura general

    list of (
        object {
            username string   //Username policy is defined in Moodle security config.
            password string  Opcional //Plain text password consisting of any characters
            createpassword int  Opcional //True if password should be created and mailed to user.
            firstname string   //The first name(s) of the user
            lastname string   //The family name of the user
            email string   //A valid and unique email address
            idnumber string  Valor por defecto para "" //An arbitrary ID code number perhaps from the institution
            calendartype string  Valor por defecto para "gregorian" //Calendar type such as "gregorian", must exist on server
            theme string  Opcional //Theme name such as "standard", must exist on server
            timezone string  Opcional //Timezone code such as Australia/Perth, or 99 for default
            mailformat int  Opcional //Mail format code is 0 for plain text, 1 for HTML etc
            description string  Opcional //User profile description, no HTML
            city string  Opcional //Home city of the user
            country string  Opcional //Home country code of the user, such as AU or CZ
            firstnamephonetic string  Opcional //The first name(s) phonetically of the user
            lastnamephonetic string  Opcional //The family name phonetically of the user
            middlename string  Opcional //The middle name of the user
            alternatename string  Opcional //The alternate name of the user
            preferences  Opcional //User preferences
            list of (
                object {
                    type string   //The name of the preference
                    value string   //The value of the preference
                }
            )
            customfields  Opcional //User custom fields (also known as user profil fields)
            list of (
                object {
                    type string   //The name of the custom field
                    value string   //The value of the custom field
                }
            )
        }
    )
    :param username:
    :param password:
    :param firstname:
    :param lastname:
    :param email:
    :param idnumber:
    :param city:
    :param country:
    :return:
    """
    auth = 'db' # Valor por defecto para "manual" //Auth plugins include manual, ldap, etc
    lang = 'es'  # Valor por defecto para "es" //Language code such as "en", must exist on server
    return call('core_user_create_users', periodo, tipourl, users=[{'username': u'%s' % username,
                                                  'password': u'Unemi*%s' % password,
                                                  'firstname': firstname,
                                                  'idnumber': idnumber,
                                                  'lastname': lastname,
                                                  'email': email,
                                                  'city': city,
                                                  'country': country,
                                                  'auth': auth,
                                                  'lang': lang}])


def CrearUsuarioManual(periodo, tipourl, username, password, firstname , lastname, email, idnumber , city, country):
    """
    Estructura general

    list of (
        object {
            username string   //Username policy is defined in Moodle security config.
            password string  Opcional //Plain text password consisting of any characters
            createpassword int  Opcional //True if password should be created and mailed to user.
            firstname string   //The first name(s) of the user
            lastname string   //The family name of the user
            email string   //A valid and unique email address
            idnumber string  Valor por defecto para "" //An arbitrary ID code number perhaps from the institution
            calendartype string  Valor por defecto para "gregorian" //Calendar type such as "gregorian", must exist on server
            theme string  Opcional //Theme name such as "standard", must exist on server
            timezone string  Opcional //Timezone code such as Australia/Perth, or 99 for default
            mailformat int  Opcional //Mail format code is 0 for plain text, 1 for HTML etc
            description string  Opcional //User profile description, no HTML
            city string  Opcional //Home city of the user
            country string  Opcional //Home country code of the user, such as AU or CZ
            firstnamephonetic string  Opcional //The first name(s) phonetically of the user
            lastnamephonetic string  Opcional //The family name phonetically of the user
            middlename string  Opcional //The middle name of the user
            alternatename string  Opcional //The alternate name of the user
            preferences  Opcional //User preferences
            list of (
                object {
                    type string   //The name of the preference
                    value string   //The value of the preference
                }
            )
            customfields  Opcional //User custom fields (also known as user profil fields)
            list of (
                object {
                    type string   //The name of the custom field
                    value string   //The value of the custom field
                }
            )
        }
    )
    :param username:
    :param password:
    :param firstname:
    :param lastname:
    :param email:
    :param idnumber:
    :param city:
    :param country:
    :return:
    """
    auth = 'manual' # Valor por defecto para "manual" //Auth plugins include manual, ldap, etc
    lang = 'es'  # Valor por defecto para "es" //Language code such as "en", must exist on server
    return call('core_user_create_users', periodo, tipourl, users=[{'username': u'%s' % username,
                                                  'password': u'Unemi*%s' % password,
                                                  'firstname': firstname,
                                                  'idnumber': idnumber,
                                                  'lastname': lastname,
                                                  'email': email,
                                                  'city': city,
                                                  'country': country,
                                                  'auth': auth,
                                                  'lang': lang}])


######################################################################################################################
######################################################################################################################
# FUNCIÓN PARA OBTENER LOS INTENTOS DEL TEST POR USUARIO Y TEST
######################################################################################################################
######################################################################################################################
def ObtenerIntentosTest(periodo, tipourl, idtest, iduser):
    """
    Estructura general

    object {
        attempts list of (
            object {
                id int  Opcional //Attempt id.
                quiz int  Opcional //Foreign key reference to the quiz that was attempted.
                userid int  Opcional //Foreign key reference to the user whose attempt this is.
                attempt int  Opcional //Sequentially numbers this students attempts at this quiz.
                uniqueid int  Opcional //Foreign key reference to the question_usage that holds the
                                                                    details of the the question_attempts that make up this quiz
                                                                    attempt.
                layout string  Opcional //Attempt layout.
                currentpage int  Opcional //Attempt current page.
                preview int  Opcional //Whether is a preview attempt or not.
                state string  Opcional //The current state of the attempts. 'inprogress',
                                                                'overdue', 'finished' or 'abandoned'.
                timestart int  Opcional //Time when the attempt was started.
                timefinish int  Opcional //Time when the attempt was submitted.
                                                                    0 if the attempt has not been submitted yet.
                timemodified int  Opcional //Last modified time.
                timemodifiedoffline int  Opcional //Last modified time via webservices.
                timecheckstate int  Opcional //Next time quiz cron should check attempt for
                                                                        state changes.  NULL means never check.
                sumgrades double  Opcional //Total marks for this attempt.
            }
        )
        warnings  Opcional //list of warnings
        list of (
            //warning
            object {
                item string  Opcional //item
                itemid int  Opcional //item id
                warningcode string   //the warning code can be used by the client app to implement specific behaviour
                message string   //untranslated english message to explain the warning
            }
        )
    }
    :param quizid:
    :param userid:
    :return:
    """
    return call('mod_quiz_get_user_attempts', periodo, tipourl, quizid=idtest, userid=iduser)


######################################################################################################################
######################################################################################################################
# FUNCIÓN PARA OBTENER INFORMACION DE LAS ACTIVIDADES
# Devuelve la lista completa de elementos de calificación para los usuarios de un curso
######################################################################################################################
######################################################################################################################
def ObtenerGradeItems(periodo, tipourl, courseid, iduser, groupid=0):
    """
    Estructura general

    object {
        usergrades list of (
            object {
                courseid int   //course id
                userid int   //user id
                userfullname string   //user fullname
                useridnumber string   //user idnumber
                maxdepth int   //table max depth (needed for printing it)
                gradeitems list of (
                    //Grade items
                    object {
                        id int   //Grade item id
                        itemname string   //Grade item name
                        itemtype string   //Grade item type
                        itemmodule string   //Grade item module
                        iteminstance int   //Grade item instance
                        itemnumber int   //Grade item item number
                        idnumber string   //Grade item idnumber
                        categoryid int   //Grade item category id
                        outcomeid int   //Outcome id
                        scaleid int   //Scale id
                        locked int  Opcional //Grade item for user locked?
                        cmid int  Opcional //Course module id (if type mod)
                        weightraw double  Opcional //Weight raw
                        weightformatted string  Opcional //Weight
                        status string  Opcional //Status
                        graderaw double  Opcional //Grade raw
                        gradedatesubmitted int  Opcional //Grade submit date
                        gradedategraded int  Opcional //Grade graded date
                        gradehiddenbydate int  Opcional //Grade hidden by date?
                        gradeneedsupdate int  Opcional //Grade needs update?
                        gradeishidden int  Opcional //Grade is hidden?
                        gradeislocked int  Opcional //Grade is locked?
                        gradeisoverridden int  Opcional //Grade overridden?
                        gradeformatted string  Opcional //The grade formatted
                        grademin double  Opcional //Grade min
                        grademax double  Opcional //Grade max
                        rangeformatted string  Opcional //Range formatted
                        percentageformatted string  Opcional //Percentage
                        lettergradeformatted string  Opcional //Letter grade
                        rank int  Opcional //Rank in the course
                        numusers int  Opcional //Num users in course
                        averageformatted string  Opcional //Grade average
                        feedback string  Opcional //Grade feedback
                        feedbackformat int  Opcional //feedback format (1 = HTML, 0 = MOODLE, 2 = PLAIN or 4 = MARKDOWN)
                    }
                )
            }
        )warnings  Opcional //list of warnings
        list of (
            //warning
            object {
                item string  Opcional //item
                itemid int  Opcional //item id
                warningcode string   //the warning code can be used by the client app to implement specific behaviour
                message string   //untranslated english message to explain the warning
            }
        )
    }
    """
    return call('gradereport_user_get_grade_items', periodo, tipourl, courseid=courseid, userid=iduser, groupid=groupid)


######################################################################################################################
######################################################################################################################
# FUNCIÓN PARA OBTENER CALIFICACIONES DE LAS ACTIVIDADES
# ** DESAPROBADO ** No vuelva a llamar a esta función. Devuelve la calificación total del curso del estudiante y
# las calificaciones de las actividades. Esta función no devuelve artículos de categoría o manuales. Esta función
# es adecuada para gerentes o profesores, no para estudiantes.
######################################################################################################################
######################################################################################################################
def ObtenerGrades(periodo, tipourl, courseid, component='', activityid=None, userids=[]):
    """
    Estructura general

    object {
        items list of (
            object {
                activityid string   //The ID of the activity or "course" for the course grade item
                itemnumber int   //Will be 0 unless the module has multiple grades
                scaleid int   //The ID of the custom scale or 0
                name string   //The module name
                grademin double   //Minimum grade
                grademax double   //Maximum grade
                gradepass double   //The passing grade threshold
                locked int   //0 means not locked, > 1 is a date to lock until
                hidden int   //0 means not hidden, > 1 is a date to hide until
                grades list of (
                    object {
                        userid int   //Student ID
                        grade double   //Student grade
                        locked int   //0 means not locked, > 1 is a date to lock until
                        hidden int   //0 means not hidden, 1 hidden, > 1 is a date to hide until
                        overridden int   //0 means not overridden, > 1 means overridden
                        feedback string   //Feedback from the grader
                        feedbackformat int   //The format of the feedback
                        usermodified int   //The ID of the last user to modify this student grade
                        datesubmitted int   //A timestamp indicating when the student submitted the activity
                        dategraded int   //A timestamp indicating when the assignment was grades
                        str_grade string   //A string representation of the grade
                        str_long_grade string   //A nicely formatted string representation of the grade
                        str_feedback string   //A formatted string representation of the feedback from the grader
                    }
                )
            }
        )outcomes  Opcional //An array of outcomes associated with the grade items
        list of (
            object {
                activityid string   //The ID of the activity or "course" for the course grade item
                itemnumber int   //Will be 0 unless the module has multiple grades
                scaleid int   //The ID of the custom scale or 0
                name string   //The module name
                locked int   //0 means not locked, > 1 is a date to lock until
                hidden int   //0 means not hidden, > 1 is a date to hide until
                grades list of (
                    object {
                        userid int   //Student ID
                        grade double   //Student grade
                        locked int   //0 means not locked, > 1 is a date to lock until
                        hidden int   //0 means not hidden, 1 hidden, > 1 is a date to hide until
                        feedback string   //Feedback from the grader
                        feedbackformat int   //The feedback format
                        usermodified int   //The ID of the last user to modify this student grade
                        str_grade string   //A string representation of the grade
                        str_feedback string   //A formatted string representation of the feedback from the grader
                    }
                )
            }
        )
    }
    """
    """
        component (Valor por defecto para "")
            A component, for example mod_forum or mod_quiz
        ---------------------------------------------------
        activityid (Valor por defecto para "null")
            The activity ID
        ---------------------------------------------------
        userids (Valor por defecto para "Array ( ) ")
            An array of user IDs, leave empty to just retrieve grade item information
        
    """
    return call('core_grades_get_grades', periodo, tipourl, courseid=courseid, component=component, activityid=activityid, userids=userids)


######################################################################################################################
######################################################################################################################
# FUNCIÓN PARA ACTUALIZAR CALIFICACIONES DE LAS ACTIVIDADES
######################################################################################################################
######################################################################################################################
def ActualizarGrades(periodo, tipourl, source, courseid, component='', activityid=None, itemnumber=0, grades=[], itemdetails=[]):
    """
    Estructura general
        int   //A value like 0 => OK, 1 => FAILED
            as defined in lib/grade/constants.php
    """
    return call('core_grades_update_grades', periodo, tipourl, source=source, courseid=courseid, component=component, activityid=activityid, itemnumber=itemnumber, grades=grades, itemdetails=itemdetails)


######################################################################################################################
######################################################################################################################
# FUNCIÓN PARA ACTUALIZAR IMAGEN DE PORTADA MOODLE
######################################################################################################################
######################################################################################################################
def ActualizarBannerCurso(course_id, periodo, tipourl, image_file, file_name):
    try:
        import time
        from datetime import datetime, timedelta, date
        import requests
        import base64
        import os
        from django.db import connections

        if tipourl == 1:
            moodle_url = f"{periodo.urlmoodle}/webservice/rest/server.php"
            webservice_token = periodo.keymoodle  #'f3202c47266fe29f2f604eca8ece6baf'
        else:
            moodle_url = f"{periodo.urlmoodle2}/webservice/rest/server.php"
            webservice_token = periodo.keymoodle2  # 'f3202c47266fe29f2f604eca8ece6baf'

        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        # Configurar los parámetros para la llamada al servicio web.
        params = {
            'wstoken': webservice_token,
            'moodlewsrestformat': 'json',
            'wsfunction': 'local_actualizarportada_actualizar_imagen_portada',
            'courseid': course_id,
            'filename': file_name,
            'imagen': base64_image
        }

        # Realizar la llamada al servicio web de Moodle.
        response = requests.post(moodle_url, data=params)
        print(response.text)
        # Verificar si la respuesta es exitosa.
        if response.status_code == 200:
            print('La imagen de portada se actualizó correctamente.')
        else:
            print('Error al actualizar la imagen de portada:', response.text)
        return True
    except Exception as ex:
        return False

