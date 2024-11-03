from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from app.models import Conversation, Message
from django.contrib import messages


def display_home(request):
  return render(request, "home.html")


@login_required
def explore_page(request):
  conversations = Conversation.objects.filter(user=request.user.id).order_by("-created_at")
  return render(request, "explore.html", {"conversations": conversations})


@login_required
def fetch_conversation(request, conversation_id):
  messages = Message.objects.filter(conversation_id=conversation_id).order_by("timestamp")
  return render(request, "partials/chat.html", {"messages": messages, "conversation_id": conversation_id})


@login_required
def new_conversation(request):
  if request.method == "POST":
    title = request.POST.get("title")
    title = title.strip()

    if len(title) > 59:
      messages.error(request, "The title is too long (max characters: 60")
      return redirect("explore")

    if Conversation.objects.filter(title=title).exists():
      messages.error(request, "A conversation with this name already exists")
      return redirect("explore")

    Conversation.objects.create(title=title, user=request.user)
    return redirect("explore")

  return redirect("explore")


@login_required
def rename_conversation(request, conversation_id):
  if request.method == "POST":
    conversation = get_object_or_404(Conversation, id=conversation_id)
    new_title = request.POST.get("new-title")

    if Conversation.objects.filter(title=new_title).exists():
      messages.error(request, "A conversation with this name already exists")
      return redirect("explore")

    conversation.title = new_title
    conversation.save()

  return redirect("explore")


@login_required
def delete_conversation(request, conversation_id):
  if request.method == "POST":
    conversation = get_object_or_404(Conversation, id=conversation_id)
    conversation.delete()
  return redirect("explore")


@login_required
def send_prompt(request, conversation_id):
  if request.method == "POST":
    prompt = request.POST.get("prompt")
    conversation = get_object_or_404(Conversation, id=conversation_id)
    Message.objects.create(is_from_user=True, text=prompt, conversation=conversation)

    messages = Message.objects.filter(conversation=conversation).order_by("timestamp")
    return render(request, "partials/chat.html", {"messages": messages, "conversation_id": conversation_id})

  return redirect("explore")
