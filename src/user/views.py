from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login


# Create your views here.
def register_user(request):
  if request.method == "POST":
    email = request.POST.get("email")
    password = request.POST.get("password")
    confirm_password = request.POST.get("confirm-password")

    if not email or not password or not confirm_password:
      messages.error(request, "Fields cannot be left empty")
      return render(request, "partial_messages.html", {"messages": messages.get_messages(request)})

    if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
      messages.error(request, "An account with this email exists")
      return render(request, "partial_messages.html", {"messages": messages.get_messages(request)})

    if password != confirm_password:
      messages.error(request, "Passwords don't match")
      return render(request, "partial_messages.html", {"messages": messages.get_messages(request)})

    try:
      validate_password(password)
    except ValidationError as errors:
      for error in errors:
        messages.error(request, error)
      return render(request, "partial_messages.html", {"messages": messages.get_messages(request)})

    User.objects.create_user(email, email, password)
    messages.success(request, "Account created under {}".format(email))
    return render(request, "partial_messages.html", {"messages": messages.get_messages(request)})

  return render(request, "register.html")

def login_user(request):
  if request.method == "POST":
    email = request.POST.get("email")
    password = request.POST.get("password")

    user = authenticate(username=email, password=password)
    if not user:
      messages.error(request, "Incorrect email or password")
      return render(request, "partial_messages.html", {"messages": messages.get_messages(request)})
    else:
      login(request, user)
      messages.success(request, "You are now logged in")
      return render(request, "partial_messages.html", {"messages": messages.get_messages(request)})

  return render(request, "login.html")

