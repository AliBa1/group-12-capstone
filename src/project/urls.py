"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from user.views import register_user,account_delete ,login_user, logout_user, manage_account, account_emailchange,account_passwordreset
from app.views import display_home, explore_page

urlpatterns = [
  path("admin/", admin.site.urls),
  path("__reload__/", include("django_browser_reload.urls")),
  path("", display_home, name="home"),
  path("register/", register_user, name="register"),
  path("login/", login_user, name="login"),
  path("logout/", logout_user, name="logout"),
  path("explore/", explore_page, name="explore"),
  path("account/", manage_account, name="account_settings"),
  path("emailchange/", account_emailchange, name="account_emailchange"),
  path("resetpassword/", account_passwordreset, name="account_passwordreset"),
  path("delete/", account_delete, name="account_delete"),
  path("accounts/", include("allauth.urls")),
  path('accounts/', include('allauth.socialaccount.urls')),
]
