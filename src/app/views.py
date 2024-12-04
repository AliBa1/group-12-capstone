from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from app.models import Conversation, Message
from django.contrib import messages
from django.http import JsonResponse
from openai import OpenAI
from django.conf import settings
import os
import joblib
import pandas as pd


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
    conversation = get_object_or_404(Conversation, id=conversation_id)
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

      response = chatbot_response(request, prompt)
      # keep below to test without using chatbot
      # response = "Test response"

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
    
  def load_model_and_data():
    try:
      model_path = os.path.join(settings.ML_MODELS_DIR, 'random_forest_model.joblib')
      encoder_path = os.path.join(settings.ML_MODELS_DIR, 'label_encoder.joblib')
      data_path = os.path.join(settings.ML_MODELS_DIR, 'processed_metro_heat_index.csv')
      
      print(f"Loading model from: {model_path}")
      
      model = joblib.load(model_path)
      label_encoder = joblib.load(encoder_path)
      data = pd.read_csv(data_path)
      
      return model, data, label_encoder
    
    except Exception as e:
      print(f"Error loading model files: {str(e)}")
      raise

  def predict_heat_index(request):
    try:
      location = request.GET.get('location', 'Houston, TX')
      print(f"Predicting for location: {location}")

      model, data, label_encoder = load_model_and_data()

      state = location.split(", ")[-1].strip()

      try:
        state_encoded = label_encoder.transform([state])[0]
      except ValueError:
        return JsonResponse({
          'error': f"State '{state}' not found in training data.",
          'available_states': label_encoder.classes_.tolist()
        }, status=400)

      location_data = data[(data["RegionName"] == location) & (data["StateName"] == state_encoded)]

      if location_data.empty:
        return JsonResponse({
          'error': f'Location not found: {location}',
          'available_locations': data["RegionName"].unique().tolist()
        }, status=404)
      
      features = location_data[["RegionID", "SizeRank", "StateName"]]
      prediction = model.predict(features)[0]

      return JsonResponse({
        'location': location,
        'predicted_heat_index': float(prediction),
        'state': state
      })

    except Exception as e:
      print(f"Prediction error: {str(e)}")
      return JsonResponse({
        'error': 'Failed to make prediction',
        'details': str(e)
      }, status=500)