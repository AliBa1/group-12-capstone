from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Conversation, Message

def display_home(request):
  return render(request, "home.html")


@login_required
def explore_page(request):
  # if request.method == "POST":
    # prompt = request.POST.get("message")
    # conversation title
    # c_title = request.POST.get("c-title")

    # message = Message.objects.create(is_from_user=True, text=prompt, )
    
  return render(request, "explore.html")

def conversations_page(request):

  return render(request, "conversations.html")
