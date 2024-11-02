from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app.models import Conversation, Message
from user.models import User
from django.contrib import messages


def display_home(request):
  return render(request, "home.html")


@login_required
def explore_page(request):
  conversations = Conversation.objects.filter(user=request.user.id).order_by("-created_at")
  active_id = request.GET.get("conversation_id")
  return render(request, "explore.html", {"conversations": conversations, "active_id": active_id})


@login_required
def conversation_chat(request, conversation_id):
  messages = Message.objects.filter(conversation_id=conversation_id).order_by("timestamp")
  return render(request, "partials/chat.html", {"messages": messages})


@login_required
def new_conversation(request):
  if request.method == "POST":
    title = request.POST.get("title")

    if Conversation.objects.filter(title=title).exists():
      messages.error(request, "A conversation with this name already exists")
      return redirect("explore")

    user = User.objects.get(id=request.user.id)
    Conversation.objects.create(title=title, user=user)

  return redirect("explore")
