import datetime
import os
import unicodedata
from django.utils.deconstruct import deconstructible
import datetime
import posixpath
from django import forms
from django.core import checks
from django.core.files.base import File
from django.core.files.images import ImageFile
from django.core.files.storage import Storage, default_storage
from django.core.files.utils import validate_file_name
from django.db.models import signals
from django.db.models.fields import Field
from django.db.models.query_utils import DeferredAttribute
from django.utils.translation import gettext_lazy as _
from django.db.models import __all__

from sga.funciones import remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode
from .storage_secret import DefaultStorageSecret
import settings
from django.utils import timezone

default_storage_secret = DefaultStorageSecret()


class FieldFileSecret(File):
    def __init__(self, instance, field, name):
        super().__init__(None, name)
        self.instance = instance
        self.field = field
        self.storage = field.storage
        self._committed = True

    def __eq__(self, other):
        # Older code may be expecting FileField values to be simple strings.
        # By overriding the == operator, it can remain backwards compatibility.
        if hasattr(other, "name"):
            return self.name == other.name
        return self.name == other

    def __hash__(self):
        return hash(self.name)

    # The standard File contains most of the necessary properties, but
    # FieldFileSecrets can be instantiated without a name, so that needs to
    # be checked for here.

    def _require_file(self):
        if not self:
            raise ValueError(
                "The '%s' attribute has no file associated with it." % self.field.name
            )

    def _get_file(self):
        self._require_file()
        if getattr(self, "_file", None) is None:
            self._file = self.storage.open(self.name, "rb")
        return self._file

    def _set_file(self, file):
        self._file = file

    def _del_file(self):
        del self._file

    file = property(_get_file, _set_file, _del_file)

    @property
    def path(self):
        self._require_file()
        return self.storage.path(self.name)

    @property
    def url(self):
        self._require_file()
        return self.storage.url(self.name)

    @property
    def size(self):
        self._require_file()
        if not self._committed:
            return self.file.size
        return self.storage.size(self.name)

    def open(self, mode="rb"):
        self._require_file()
        if getattr(self, "_file", None) is None:
            self.file = self.storage.open(self.name, mode)
        else:
            self.file.open(mode)
        return self

    # open() doesn't alter the file's contents, but it does reset the pointer
    open.alters_data = True

    # In addition to the standard File API, FieldFileSecrets have extra methods
    # to further manipulate the underlying file, as well as update the
    # associated model instance.

    def save(self, name, content, save=True):
        name = self.field.generate_filename(self.instance, name)
        self.name = self.storage.save(name, content, max_length=self.field.max_length)
        setattr(self.instance, self.field.attname, self.name)
        self._committed = True

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()

    save.alters_data = True

    def delete(self, save=True):
        if not self:
            return
        # Only close the file if it's already open, which we know by the
        # presence of self._file
        if hasattr(self, "_file"):
            self.close()
            del self.file

        self.storage.delete(self.name)

        self.name = None
        setattr(self.instance, self.field.attname, self.name)
        self._committed = False

        if save:
            self.instance.save()

    delete.alters_data = True

    @property
    def closed(self):
        file = getattr(self, "_file", None)
        return file is None or file.closed

    def close(self):
        file = getattr(self, "_file", None)
        if file is not None:
            file.close()

    def __getstate__(self):
        # FieldFileSecret needs access to its associated model field, an instance and
        # the file's name. Everything else will be restored later, by
        # FileDescriptor below.
        return {
            "name": self.name,
            "closed": False,
            "_committed": True,
            "_file": None,
            "instance": self.instance,
            "field": self.field,
        }

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.storage = self.field.storage


class FileSecretDescriptor(DeferredAttribute):

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        # This is slightly complicated, so worth an explanation.
        # instance.file`needs to ultimately return some instance of `File`,
        # probably a subclass. Additionally, this returned object needs to have
        # the FieldFileSecret API so that users can easily do things like
        # instance.file.path and have that delegated to the file storage engine.
        # Easy enough if we're strict about assignment in __set__, but if you
        # peek below you can see that we're not. So depending on the current
        # value of the field we have to dynamically construct some sort of
        # "thing" to return.

        # The instance dict contains whatever was originally assigned
        # in __set__.
        file = super().__get__(instance, cls)

        # If this value is a string (instance.file = "path/to/file") or None
        # then we simply wrap it with the appropriate attribute class according
        # to the file field. [This is FieldFileSecret for FileFields and
        # ImageFieldFileSecret for ImageFields; it's also conceivable that user
        # subclasses might also want to subclass the attribute class]. This
        # object understands how to convert a path to a file, and also how to
        # handle None.
        if isinstance(file, str) or file is None:
            attr = self.field.attr_class(instance, self.field, file)
            instance.__dict__[self.field.attname] = attr

        # Other types of files may be assigned as well, but they need to have
        # the FieldFileSecret interface added to them. Thus, we wrap any other type of
        # File inside a FieldFileSecret (well, the field's attr_class, which is
        # usually FieldFileSecret).
        elif isinstance(file, File) and not isinstance(file, FieldFileSecret):
            file_copy = self.field.attr_class(instance, self.field, file.name)
            file_copy.file = file
            file_copy._committed = False
            instance.__dict__[self.field.attname] = file_copy

        # Finally, because of the (some would say boneheaded) way pickle works,
        # the underlying FieldFileSecret might not actually itself have an associated
        # file. So we need to reset the details of the FieldFileSecret in those cases.
        elif isinstance(file, FieldFileSecret) and not hasattr(file, "field"):
            file.instance = instance
            file.field = self.field
            file.storage = self.field.storage

        # Make sure that the instance is correct.
        elif isinstance(file, FieldFileSecret) and instance is not file.instance:
            file.instance = instance

        # That was fun, wasn't it?
        return instance.__dict__[self.field.attname]

    def __set__(self, instance, value):
        instance.__dict__[self.field.attname] = value


class FileSecretField(Field):
    # The class to wrap instance attributes in. Accessing the file object off
    # the instance will always return an instance of attr_class.
    attr_class = FieldFileSecret

    # The descriptor to use for accessing the attribute off of the class.
    descriptor_class = FileSecretDescriptor

    description = _("File")

    def __init__(self, verbose_name=None, name=None, upload_to="", storage=None, **kwargs):
        self._primary_key_set_explicitly = "primary_key" in kwargs

        self.storage = default_storage_secret
        if callable(self.storage):
            # Hold a reference to the callable for deconstruct().
            self._storage_callable = self.storage
            self.storage = self.storage()
            if not isinstance(self.storage, Storage):
                raise TypeError(
                    "%s.storage must be a subclass/instance of %s.%s" % (self.__class__.__qualname__, Storage.__module__, Storage.__qualname__,)
                )
        self.upload_to = upload_to

        kwargs.setdefault("max_length", 100)
        super().__init__(verbose_name, name, **kwargs)

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_primary_key(),
            *self._check_upload_to(),
        ]

    def _check_primary_key(self):
        if self._primary_key_set_explicitly:
            return [
                checks.Error(
                    "'primary_key' is not a valid argument for a %s."
                    % self.__class__.__name__,
                    obj=self,
                    id="fields.E201",
                )
            ]
        else:
            return []

    def _check_upload_to(self):
        if isinstance(self.upload_to, str) and self.upload_to.startswith("/"):
            return [
                checks.Error(
                    "%s's 'upload_to' argument must be a relative path, not an "
                    "absolute path." % self.__class__.__name__,
                    obj=self,
                    id="fields.E202",
                    hint="Remove the leading slash.",
                )
            ]
        else:
            return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get("max_length") == 100:
            del kwargs["max_length"]
        kwargs["upload_to"] = self.upload_to
        if self.storage is not default_storage_secret:
            kwargs["storage"] = getattr(self, "_storage_callable", self.storage)
        return name, path, args, kwargs

    def get_internal_type(self):
        return "FileField"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        # Need to convert File objects provided via a form to string for
        # database insertion.
        if value is None:
            return None
        return str(value)

    def pre_save(self, model_instance, add):
        file = super().pre_save(model_instance, add)
        if file and not file._committed:
            # Commit the file to storage prior to saving the model
            file.save(file.name, file.file, save=False)
        return file

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.attname, self.descriptor_class(self))

    def generate_filename(self, instance, filename):
        """
        Apply (if callable) or prepend (if a string) upload_to to the filename,
        then delegate further processing of the name to the storage backend.
        Until the storage layer, all file paths are expected to be Unix style
        (with forward slashes).
        """
        if callable(self.upload_to):
            filename = self.upload_to(instance, filename)
        else:
            dirname = datetime.datetime.now().strftime(str(self.upload_to))
            filename = posixpath.join(dirname, filename)
        filename = validate_file_name(filename, allow_relative_path=True)
        return self.storage.generate_filename(filename)

    def save_form_data(self, instance, data):
        # Important: None means "no change", other false value means "clear"
        # This subtle distinction (rather than a more explicit marker) is
        # needed because we need to consume values that are also sane for a
        # regular (non Model-) Form to find in its cleaned_data dictionary.
        if data is not None:
            # This value will be converted to str and stored in the
            # database, so leaving False as-is is not acceptable.
            setattr(instance, self.name, data or "")

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": forms.FileField,
                "max_length": self.max_length,
                **kwargs,
            }
        )


@deconstructible
class UploadToPath(object):

    def __init__(self, upload_to):
        self.upload_to = upload_to

    def __call__(self, instance, filename):
        folder_name = instance.folder_name()
        return self.generate_filename(folder_name, filename)

    def get_directory_name(self):
        return os.path.normpath(datetime.datetime.now().strftime(self.upload_to))

    def get_filename(self, filename):
        from django.utils.text import slugify
        filename = default_storage.get_valid_name(os.path.basename(filename))
        filename = filename
        filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
        extension = os.path.splitext(filename)[1][1:]
        file_name = os.path.splitext(filename)[0]
        return os.path.normpath("%s.%s" % (slugify(file_name).upper(), extension.lower()))

    def generate_filename(self, folder_, filename):
        return os.path.join(folder_, self.upload_to, self.get_filename(filename))


@deconstructible
class UploadToPathDepartamento(object):

    def __init__(self, upload_to):
        self.upload_to = upload_to

    def __call__(self, instance, filename):
        nombredepartamento, nombregestion = instance.carpeta.gestion.departamento.nomslug, instance.carpeta.gestion.nomslug
        primeracarpeta_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(str(instance.carpeta.primera_carpeta()).lower())).replace('-', '_')
        return self.generate_filename(nombredepartamento, nombregestion, primeracarpeta_, filename)

    def get_directory_name(self):
        return os.path.normpath(datetime.datetime.now().strftime(self.upload_to))

    def get_filename(self, filename):
        from django.utils.text import slugify
        filename = default_storage.get_valid_name(os.path.basename(filename))
        filename = filename
        filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
        extension = os.path.splitext(filename)[1][1:]
        file_name = os.path.splitext(filename)[0]
        # return os.path.normpath("%s.%s" % (slugify(file_name).upper(), extension.lower()))
        return os.path.normpath("%s.%s" % (slugify(file_name), extension.lower()))

    def generate_filename(self, departamento_, gestion_, folder_, filename):
        return os.path.join(departamento_, gestion_, folder_, self.upload_to, self.get_filename(filename))


@deconstructible
class UploadToPathDepartamentoGestion(object):

    def __init__(self, upload_to):
        self.upload_to = upload_to

    def __call__(self, instance, filename):
        folder_name_departamento = instance.folder_name()
        folder_name_gestion = instance.folder_name()
        return self.generate_filename(folder_name_departamento, folder_name_gestion, filename)

    def get_directory_name(self):
        return os.path.normpath(datetime.datetime.now().strftime(self.upload_to))

    def get_filename(self, filename):
        from django.utils.text import slugify
        filename = default_storage.get_valid_name(os.path.basename(filename))
        filename = filename
        filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
        extension = os.path.splitext(filename)[1][1:]
        file_name = os.path.splitext(filename)[0]
        return os.path.normpath("%s.%s" % (slugify(file_name).upper(), extension.lower()))

    def generate_filename(self, folder_, subfolder_, filename):
        return os.path.join(folder_, subfolder_, self.upload_to, self.get_filename(filename))


__all__ += ["FileSecretField"]
