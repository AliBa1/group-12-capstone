from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from app.models import Conversation, Message
from django.http import JsonResponse
from openai import OpenAI
from django.conf import settings
from app.constants import cities
from app.utils import choose_premade_prompts, is_title_valid


def display_home(request):
  return render(request, "home.html")


@login_required
def explore_page(request):
  conversations = Conversation.objects.filter(user=request.user.id).order_by("-created_at")
  return render(request, "explore.html", {"conversations": conversations, "cities": cities})


@login_required
def fetch_conversation(request, conversation_id):
  chat_messages = Message.objects.filter(conversation_id=conversation_id).order_by("timestamp")
  conversation = get_object_or_404(Conversation, id=conversation_id)

  return render(
    request,
    "partials/chat.html",
    {
      "chat_messages": chat_messages,
      "conversation_id": conversation_id,
      "bot_typing": False,
      "prompt": None,
      "premade_prompts": choose_premade_prompts(conversation),
      "city": conversation.city,
      "reason": conversation.reason,
    },
  )


@login_required
def new_conversation(request):
  if request.method == "POST":
    title = request.POST.get("title")
    title = title.strip()
    city = request.POST.get("city")
    reason = request.POST.get("reason")

    is_valid = is_title_valid(request, title)

    if is_valid:
      Conversation.objects.create(title=title, city=city, reason=reason, user=request.user)

  return redirect("explore")


@login_required
def edit_conversation(request, conversation_id):
  if request.method == "POST":
    conversation = get_object_or_404(Conversation, id=conversation_id)
    new_title = request.POST.get("updated-title")
    new_city = request.POST.get("updated-city")
    new_reason = request.POST.get("updated-reason")

    is_valid = is_title_valid(request, new_title)

    if is_valid:
      conversation.title = new_title
      conversation.city = new_city
      conversation.reason = new_reason
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
    premade_prompt = request.POST.get("premade-prompt")
    if premade_prompt:
      premade_prompt = premade_prompt.lower()
    conversation = get_object_or_404(Conversation, id=conversation_id)
    city = conversation.city
    reason = conversation.reason

    if premade_prompt:
      # use vars premade_prompt, city, and reason to enter into model however you please
      prompt = "I want to learn more about " + premade_prompt + " in " + city
      Message.objects.create(is_from_user=True, text=prompt, conversation=conversation)
    else:
      # use vars prompt, city, and reason to enter into model however you please
      Message.objects.create(is_from_user=True, text=prompt, conversation=conversation)

    chat_messages = Message.objects.filter(conversation=conversation).order_by("timestamp")
    return render(
      request,
      "partials/chat.html",
      {
        "chat_messages": chat_messages,
        "conversation_id": conversation_id,
        "bot_typing": True,
        "prompt": prompt,
        "premade_prompts": choose_premade_prompts(conversation),
        "city": conversation.city,
        "reason": conversation.reason,
      },
    )

  return redirect("explore")


@login_required
def send_response(request, conversation_id, prompt):
  if request.method == "POST":
    try:
      conversation = get_object_or_404(Conversation, id=conversation_id)

      response = chatbot_response(request, prompt)
      # keep below to test without using chatbot
      # response = "Test response"

      if isinstance(response, JsonResponse):
        Message.objects.create(
          is_from_user=False,
          text="An error occurred processing your request. Please refresh and try again.",
          conversation=conversation,
        )
      else:
        Message.objects.create(is_from_user=False, text=response, conversation=conversation)

      chat_messages = Message.objects.filter(conversation=conversation).order_by("timestamp")
      return render(
        request,
        "partials/chat.html",
        {
          "chat_messages": chat_messages,
          "conversation_id": conversation_id,
          "bot_typing": False,
          "prompt": None,
          "premade_prompts": choose_premade_prompts(conversation),
          "city": conversation.city,
          "reason": conversation.reason,
        },
      )
    except Exception as e:
      print("Error:", e)
      return JsonResponse({"error": "An error occurred processing your request."}, status=500)
  return redirect("explore")


# colter's functions below
@login_required
def chatbot_response(request, prompt):
  if request.method == "POST":
    try:
      client = OpenAI(api_key=settings.OPENAI_API_KEY)
      thread = client.beta.threads.create()
      client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt)
      run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id="asst_oiJLKxsdKui3utTSaBFGuwST",
        instructions="Please assist the user with travel and relocation inquiries",
      )
      if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        assistant_message = ""
        for message in messages:
          if message.role == "assistant":
            for content_block in message.content:
              if content_block.type == "text":
                assistant_message = content_block.text.value
            break
        return (
          assistant_message
          if assistant_message
          else JsonResponse({"error": "No assistant response found."}, status=500)
        )
      else:
        return JsonResponse({"error": f"Run status: {run.status}"}, status=500)
    except Exception as e:
      print("Error:", e)
      return JsonResponse({"error": "An error occured processing your request"}, status=500)


"""
@login_required
def chatbot_response(request, prompt):
  if request.method == 'POST':
    try:
      if not isinstance(prompt, str):
        return JsonResponse({"error": "Invalid message format"}, status=400)

      completion = .chat.completions.create(
        model="gpt-4o-mini",
        messages=[
          {
            "role": "system",
            "content": "You are a helpful travel assistant. Help people looking to vacation/relocate find a destination.",
          },
          {"role": "user", "content": prompt},
        ],
      )
      chatbot_message = completion.choices[0].message.content
      # return JsonResponse({'response': chatbot_message})
      return chatbot_message
    except Exception as e:
      print("Error:", e)
      return JsonResponse({'error': 'An error occurred processing your request.'}, status=500)
      """
