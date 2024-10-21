from django.shortcuts import render

# Create your views here.
def display_base(request):
  return render(request, "base.html")