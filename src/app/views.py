from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from app.models import Conversation, Message
from django.contrib import messages
from django.http import JsonResponse
from openai import OpenAI
from django.conf import settings


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
    request, "partials/chat.html", {"chat_messages": chat_messages, "conversation_id": conversation_id, "bot_typing": False, "prompt": None}
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
    premade_prompt = request.POST.get("pre-made-prompt")
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if premade_prompt:
      city = "Los Angeles, CA"
      prompt = "I want to learn more about " + premade_prompt.lower() + " in " + city
      Message.objects.create(is_from_user=True, text=prompt, conversation=conversation)
    else:
      Message.objects.create(is_from_user=True, text=prompt, conversation=conversation)

    chat_messages = Message.objects.filter(conversation=conversation).order_by("timestamp")
    return render(
      request, "partials/chat.html", {"chat_messages": chat_messages, "conversation_id": conversation_id, "bot_typing": True, "prompt": prompt}
    )

  return redirect("explore")


@login_required
def send_response(request, conversation_id, prompt):
  if request.method == "POST":
    try:
      conversation = get_object_or_404(Conversation, id=conversation_id)

      # response = chatbot_response(request, prompt)
      # keep below to test without using chatbot
      response = "Test response"

      if isinstance(response, JsonResponse):
        Message.objects.create(is_from_user=False, text="An error occurred processing your request. Please refresh and try again.", conversation=conversation)
      else:
        Message.objects.create(is_from_user=False, text=response, conversation=conversation)

      chat_messages = Message.objects.filter(conversation=conversation).order_by("timestamp")
      return render(
        request,
        "partials/chat.html",
        {"chat_messages": chat_messages, "conversation_id": conversation_id, "bot_typing": False, "prompt": None},
      )
    except Exception as e:
      print("Error:", e)
      return JsonResponse({'error': 'An error occurred processing your request.'}, status=500)
  return redirect("explore")



@login_required
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