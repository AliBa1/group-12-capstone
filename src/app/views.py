from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def display_home(request):
  return render(request, "home.html")


@login_required
def explore_page(request):
  return render(request, "explore.html")
