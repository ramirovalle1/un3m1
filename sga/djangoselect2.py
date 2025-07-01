from django.contrib.auth.mixins import LoginRequiredMixin
from django_select2.forms import ModelSelect2Widget


class LoginRequired(LoginRequiredMixin):
    login_url = "/"


class MySelect2Widget(ModelSelect2Widget):
    search_fields = []

    def __init__(self, searchs=None, *args, **kwargs):
        self.search_fields = searchs
        super().__init__(*args, **kwargs)
