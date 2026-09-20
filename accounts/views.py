from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class SiteLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
