from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from app.models import Conversation, Message


def display_home(request):
  return render(request, "home.html")


@login_required
def explore_page(request):
  conversations = Conversation.objects.all()
  active_id = request.GET.get("conversation_id")
  return render(request, "explore.html", {"conversations": conversations, "active_id": active_id})


def conversation_chat(request, conversation_id):
  messages = Message.objects.filter(conversation_id=conversation_id).order_by("timestamp")
  return render(request, "partials/chat.html", {"messages": messages})
