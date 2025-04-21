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
from user.views import (
  register_user,
  account_delete,
  login_user,
  logout_user,
  manage_account,
  account_emailchange,
  account_passwordreset,
)
from app.views import (
  display_home,
  chatbot_page,
  fetch_conversation,
  new_conversation,
  edit_conversation,
  delete_conversation,
  send_prompt,
  send_response,
  chatbot_response,
  proxy_hotel_photo,
  explore_page,
  update_city_reason,
  send_search,
  search_response,
  predict_heat_index,
  last_heat_index,
  update_preferences
)

urlpatterns = [
  path("admin/", admin.site.urls),
  path("__reload__/", include("django_browser_reload.urls")),
  path("", display_home, name="home"),
  path("register/", register_user, name="register"),
  path("login/", login_user, name="login"),
  path("logout/", logout_user, name="logout"),
  path("chatbot/", chatbot_page, name="chatbot"),
  path("fetch_conversation/<int:conversation_id>/", fetch_conversation, name="fetch_conversation"),
  path("new_conversation/", new_conversation, name="new_conversation"),
  path("send_prompt/<int:conversation_id>/", send_prompt, name="send_prompt"),
  path("send_response/<int:conversation_id>/<path:prompt>", send_response, name="send_response"),
  path("edit_conversation/<int:conversation_id>/", edit_conversation, name="edit_conversation"),
  path("delete_conversation/<int:conversation_id>/", delete_conversation, name="delete_conversation"),
  path("account/", manage_account, name="account_settings"),
  path("emailchange/", account_emailchange, name="account_emailchange"),
  path("resetpassword/", account_passwordreset, name="account_passwordreset"),
  path("delete/", account_delete, name="account_delete"),
  path("accounts/", include("allauth.urls")),
  path("accounts/", include("allauth.socialaccount.urls")),
  path("api/chatbot/", chatbot_response, name="chatbot_response"),
  path('heat_index/', predict_heat_index, name='predict_heat_index'),
  path("hotel-photo/<path:photo_reference>/", proxy_hotel_photo, name="proxy_hotel_photo"),
  path("explore/", explore_page, name="explore"),
  path("update_city_reason/", update_city_reason, name="update_city_reason"),
  # path("send_search/<str:city>/<str:reason>", send_search, name="send_search"),
  path("send_search/", send_search, name="send_search"),
  path("search_response/<str:city>/<str:topic>", search_response, name="search_response"),
  path('heat_index/', predict_heat_index, name='predict_heat_index'),
  path('last_heat_index/', last_heat_index, name='last_heat_index'),
  path('update_preferences/<str:property_type>', update_preferences, name='update_preferences'),
]
