from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import EmailForm


# Create your views here.
def register_user(request):
  if request.method == "POST":
    email = request.POST.get("email")
    password = request.POST.get("password")
    confirm_password = request.POST.get("confirm-password")

    if not email or not password or not confirm_password:
      messages.error(request, "Fields cannot be left empty")
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
      messages.error(request, "An account with this email exists")
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    if password != confirm_password:
      messages.error(request, "Passwords don't match")
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    try:
      validate_password(password)
    except ValidationError as errors:
      for error in errors:
        messages.error(request, error)
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    user = User.objects.create_user(email, email, password)
    user = authenticate(request, username=email, password=password)
    if user:
      login(request, user)

    messages.success(request, "Account created under {}".format(email))
    response = HttpResponse()
    response["HX-Redirect"] = "/explore"
    return response

  return render(request, "register.html")


def login_user(request):
  if request.method == "POST":
    email = request.POST.get("email")
    password = request.POST.get("password")

    user = authenticate(username=email, password=password)
    if not user:
      messages.error(request, "Incorrect email or password")
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})
    else:
      login(request, user)
      messages.success(request, "You have been logged in.")
      response = HttpResponse()
      response["HX-Redirect"] = "/explore"
      return response
  return render(request, "login.html")


def logout_user(request):
  logout(request)
  messages.success(request, "You have been logged out.")
  return redirect("/")


def manage_account(request):
  return render(request, "account/account_settings.html")


@login_required(login_url="login")
def account_emailchange(request):
  if "HX-Request" in request.headers:
    form = EmailForm(instance=request.user)
    return render(request, "partials/email_change.html", {"form": form})

  if request.method == "POST":
    form = EmailForm(request.POST, instance=request.user)

    if form.is_valid():
      email = form.cleaned_data["email"]
      # Check if email already exists
      if (
        User.objects.filter(email=email).exclude(id=request.user.id).exists()
        or User.objects.filter(username=email).exclude(id=request.user.id).exists()
      ):
        messages.warning(request, f"{email} is already in use.")
        return redirect("account_settings")

      user = request.user
      user.email = email
      user.username = email
      user.save()

      messages.success(request, "Your email has been updated successfully.")
      return redirect("account_settings")
    else:
      messages.warning(request, "Form not valid.")
      return redirect("account_settings")
  return redirect("/")


# views.py
@login_required(login_url="login")
def account_passwordreset(request):
  if request.method == "POST":
    old_password = request.POST.get("old_password")
    new_password = request.POST.get("new_password")
    confirm_password = request.POST.get("confirm_password")

    if not old_password or not new_password or not confirm_password:
      messages.error(request, "All fields are required")
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    # Verify old pass
    if not request.user.check_password(old_password):
      messages.error(request, "Current password is incorrect")
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    # Check if pass match
    if new_password != confirm_password:
      messages.error(request, "New passwords don't match")
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    # Validate new pass
    try:
      validate_password(new_password, request.user)
    except ValidationError as errors:
      for error in errors:
        messages.error(request, error)
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    # Check if new passis same as old pass
    if old_password == new_password:
      messages.error(request, "New password cannot be the same as current password")
      return render(request, "includes/partial_messages.html", {"messages": messages.get_messages(request)})

    # Update pass
    request.user.set_password(new_password)
    request.user.save()

    # Keep user logged in
    update_session_auth_hash(request, request.user)

    messages.success(request, "Password updated successfully")
    response = HttpResponse()
    response["HX-Redirect"] = reverse("account_settings")
    return response

  return render(request, "partials/password_reset.html")


@login_required
def account_delete(request):
  user = request.user
  if request.method == "POST":
    logout(request)
    user.delete()
    messages.error(request, "Account deleted.")
    return redirect("/")

  return render(request, "partials/delete_account.html")
