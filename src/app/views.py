from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from app.models import Conversation, Message
from django.contrib import messages
from django.http import JsonResponse
from openai import OpenAI
from django.conf import settings
import json


def display_home(request):
  return render(request, "home.html")


@login_required
def explore_page(request):
  conversations = Conversation.objects.filter(user=request.user.id).order_by("-created_at")
  return render(request, "explore.html", {"conversations": conversations})


@login_required
def fetch_conversation(request, conversation_id):
  chat_messages = Message.objects.filter(conversation_id=conversation_id).order_by("timestamp")
  return render(
    request, "partials/chat.html", {"chat_messages": chat_messages, "conversation_id": conversation_id, "bot_typing": False}
  )


def is_title_valid(request, title):
  if request.method == "POST":
    if len(title) < 1:
      messages.error(request, "The title can not be empty")
      return False

    if len(title) > 59:
      messages.error(request, "The title is too long (max characters: 60)")
      return False

    if Conversation.objects.filter(title=title).exists():
      messages.error(request, "A conversation with this title already exists")
      return False
  return True


@login_required
def new_conversation(request):
  if request.method == "POST":
    title = request.POST.get("title")
    title = title.strip()

    is_valid = is_title_valid(request, title)

    if is_valid:
      Conversation.objects.create(title=title, user=request.user)

  return redirect("explore")


@login_required
def rename_conversation(request, conversation_id):
  if request.method == "POST":
    conversation = get_object_or_404(Conversation, id=conversation_id)
    new_title = request.POST.get("new-title")

    is_valid = is_title_valid(request, new_title)

    if is_valid:
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

    # render prompt
    chat_messages = Message.objects.filter(conversation=conversation).order_by("timestamp")
    render(
      request, "partials/chat.html", {"chat_messages": chat_messages, "conversation_id": conversation_id, "bot_typing": True}
    )

    # model sends a response from this function
    send_response(request, conversation, prompt)

    # get all messages to render
    chat_messages = Message.objects.filter(conversation=conversation).order_by("timestamp")
    return render(
      request,
      "partials/chat.html",
      {"chat_messages": chat_messages, "conversation_id": conversation_id, "bot_typing": False},
    )

  return redirect("explore")


@login_required
def send_response(request, conversation, prompt):
  if request.method == "POST":
    # pass through model here
    response = chatbot_response(request, prompt)
    if isinstance(response, JsonResponse):
      Message.objects.create(is_from_user=False, text="An error occured getting response from ChatGPT", conversation=conversation)
    else:
      Message.objects.create(is_from_user=False, text=response, conversation=conversation)

    # response = "I have received your message"
    # Message.objects.create(is_from_user=False, text=response, conversation=conversation)
    return
  return


def chatbot_response(request, prompt):
  if request.method == 'POST':
    try:
      client = OpenAI(api_key=settings.OPENAI_API_KEY)
      # data = json.loads(request.body)
      # user_message = data.get('message')
      if not isinstance(prompt, str):
        return JsonResponse({'error': 'Invalid message format'}, status=400)

      completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
          {"role": "system", "content": "You are a helpful travel assistant. Help people looking to vacation/relocate find a destination."},
          {"role": "user", "content": prompt}
        ]
      )
      chatbot_message = completion.choices[0].message.content
      # return JsonResponse({'response': chatbot_message})
      return chatbot_message
    except Exception as e:
      print("Error:", e)
      return JsonResponse({'error': 'An error occurred processing your request.'}, status=500)