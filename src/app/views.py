from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from openai import OpenAI
from django.conf import settings
import json


def display_home(request):
  return render(request, "home.html")


@login_required
def explore_page(request):
  return render(request, "explore.html")


def chatbot_response(request):
  if request.method == 'POST':
    try:
      client = OpenAI(api_key=settings.CHATGPT_API_KEY)
      data = json.loads(request.body)
      user_message = data.get('message')
      if not isinstance(user_message, str):
        return JsonResponse({'error': 'Invalid message format'}, status=400)

      completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
          {"role": "system", "content": "You are a helpful travel assistant. Help people looking to vacation/relocate find a destination."},
          {"role": "user", "content": user_message}
        ]
      )
      chatbot_message = completion.choices[0].message.content
      return JsonResponse({'response': chatbot_message})
    except Exception as e:
      print("Error:", e)
      return JsonResponse({'error': 'An error occurred processing your request.'}, status=500)