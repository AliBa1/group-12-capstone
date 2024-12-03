import json
import requests
import googlemaps
from openai import OpenAI
from django.conf import settings
from app.constants import cities
from app.models import Conversation, Message
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_http_methods
from app.utils import choose_premade_prompts, choose_topics, is_title_valid
from .services.travel_service_factory import TravelServiceFactory
from .services.hotel_service import HotelSearchStrategy
from .services.flight_service import FlightSearchStrategy
from .services.car_rental_service import CarRentalSearchStrategy
from .services.housing_service import HousingSearchStrategy
from .services.apartments_service import ApartmentSearchStrategy


travel_factory = TravelServiceFactory()
travel_factory.register_strategy(HotelSearchStrategy())
travel_factory.register_strategy(FlightSearchStrategy())
travel_factory.register_strategy(CarRentalSearchStrategy())
travel_factory.register_strategy(HousingSearchStrategy())
travel_factory.register_strategy(ApartmentSearchStrategy())


def display_home(request):
  return render(request, "home.html")


@login_required
def chatbot_page(request):
  latest_conversation = Conversation.objects.filter(user=request.user.id).order_by("-created_at").first()

  locations = []
  if latest_conversation:
    latest_message = (
      Message.objects.filter(conversation=latest_conversation).filter(is_from_user=False).order_by("-timestamp").first()
    )

    if latest_message and latest_message.additional_data:
      try:
        data = latest_message.additional_data
        if "hotels" in data:
          locations = [
            {"lat": hotel["details"]["location"]["lat"], "lng": hotel["details"]["location"]["lng"]}
            for hotel in data["hotels"]
            if "details" in hotel and "location" in hotel["details"]
          ]
      except Exception as e:
        print(f"Error extracting locations: {e}")

  if not locations:
    locations = [
      {"lat": -33.8688, "lng": 151.2093},
    ]

  conversations = Conversation.objects.filter(user=request.user.id).order_by("-created_at")
  return render(
    request,
    "chatbot.html",
    {
      "conversations": conversations,
      "cities": cities,
      "locations": json.dumps(locations),
      "google_maps_api_key": settings.GOOGLE_PLACES_API_KEY,
    },
  )


@login_required
def fetch_conversation(request, conversation_id):
  chat_messages = Message.objects.filter(conversation_id=conversation_id).order_by("timestamp")
  conversation = get_object_or_404(Conversation, id=conversation_id)

  locations = []
  latest_hotel_message = (
    Message.objects.filter(
      conversation=conversation,
      is_from_user=False,
      additional_data__isnull=False,
    )
    .order_by("-timestamp")
    .first()
  )

  if latest_hotel_message and latest_hotel_message.additional_data:
    data = latest_hotel_message.additional_data
    if "hotels" in data:
      locations = [
        {"lat": hotel["details"]["location"]["lat"], "lng": hotel["details"]["location"]["lng"]}
        for hotel in data["hotels"]
        if "details" in hotel and "location" in hotel["details"]
      ]
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
      "locations": json.dumps(locations),
      # "map_center": json.dumps(map_center) if map_center else None,
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

  return redirect("chatbot")


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

  return redirect("chatbot")


@login_required
def delete_conversation(request, conversation_id):
  if request.method == "POST":
    conversation = get_object_or_404(Conversation, id=conversation_id)
    conversation.delete()
  return redirect("chatbot")


@login_required
def send_prompt(request, conversation_id):
  if request.method == "POST":
    prompt = request.POST.get("prompt")
    premade_prompt = request.POST.get("premade-prompt")
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if premade_prompt:
      premade_prompt = premade_prompt.lower()
      prompt = f"I want to learn more about {premade_prompt} in {conversation.city}"

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

  return redirect("chatbot")


@login_required
def send_response(request, conversation_id, prompt):
  if request.method == "POST":
    try:
      conversation = get_object_or_404(Conversation, id=conversation_id)

      request.POST = request.POST.copy()
      request.POST["conversation_id"] = conversation_id

      response = chatbot_response(request, prompt)

      if isinstance(response, JsonResponse):
        Message.objects.create(
          is_from_user=False,
          text="An error occurred processing your request. Please refresh and try again.",
          conversation=conversation,
        )
      else:
        response_text = response.get("response", "No response generated")
        message = Message.objects.create(is_from_user=False, text=response_text, conversation=conversation)

        if "data" in response:
          message.additional_data = response["data"]
          message.save()
        locations = []
        if "data" in response:
          message.additional_data = response["data"]
          message.save()

          if "hotels" in response["data"]:
            locations = [
              {"lat": hotel["details"]["location"]["lat"], "lng": hotel["details"]["location"]["lng"]}
              for hotel in response["data"]["hotels"]
              if "details" in hotel and "location" in hotel["details"]
            ]

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
          "locations": json.dumps(locations),
        },
      )
    except Exception as e:
      print("Error:", e)
      return JsonResponse({"error": "An error occurred processing your request."}, status=500)

  return redirect("chatbot")


# colter's function below
def chatbot_response(request, prompt):
  if request.method == "POST":
    try:
      client = OpenAI(api_key=settings.OPENAI_API_KEY)
      thread = client.beta.threads.create()
      client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt)

      run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id="asst_oiJLKxsdKui3utTSaBFGuwST",
        instructions="Please assist the user with travel and relocation inquiries. When responding to travel and relocation queries, provide ONLY a brief, one-sentence welcome or introduction",
      )

      if run.status != "completed":
        return JsonResponse({"error": f"Run status: {run.status}"}, status=500)

      messages = client.beta.threads.messages.list(thread_id=thread.id)
      assistant_message = ""
      for message in messages:
        if message.role == "assistant":
          for content_block in message.content:
            if content_block.type == "text":
              assistant_message = content_block.text.value
          break

      if not assistant_message:
        return JsonResponse({"error": "No assistant response found."}, status=500)

      strategy = travel_factory.get_strategy(prompt)
      if strategy:
        conversation_id = request.POST.get("conversation_id")
        city = None
        if conversation_id:
          conversation = get_object_or_404(Conversation, id=conversation_id)
          city = conversation.city

        strategy_response = strategy.process_query(prompt, city=city)
        if strategy_response:
          if isinstance(strategy_response, dict):
            assistant_message = f"{assistant_message} {strategy_response.get('text', '')}"
            return {"response": assistant_message, "data": strategy_response.get("data")}
          else:
            assistant_message = f"{assistant_message} {strategy_response}"

      return {"response": assistant_message}

    except Exception as e:
      print(f"Error in chatbot_response: {str(e)}")
      return JsonResponse({"error": f"Error: {str(e)}"}, status=500)


@require_http_methods(["GET"])
@cache_page(60 * 60 * 24)  # cache for 24 hours
def proxy_hotel_photo(request, photo_reference):
  if not photo_reference:
    return HttpResponseNotFound("No photo reference provided")

  try:
    gmaps = googlemaps.Client(key=settings.GOOGLE_PLACES_API_KEY)
    base_url = "https://maps.googleapis.com/maps/api/place/photo"
    params = {"maxwidth": 400, "photoreference": photo_reference, "key": settings.GOOGLE_PLACES_API_KEY}

    response = requests.get(base_url, params=params, stream=True)

    if response.status_code == 200:
      return HttpResponse(response.content, content_type=response.headers.get("Content-Type", "image/jpeg"))
    return HttpResponseNotFound("Photo not found")

  except Exception as e:
    print(f"Error proxying photo: {str(e)}")
    return HttpResponseNotFound("Error retrieving photo")


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


@login_required
def explore_page(request):
  return render(
    request,
    "explore.html",
    {
      "cities": cities,
    },
  )


@login_required
def update_city_reason(request):
  if request.method == "POST":
    city = request.POST.get("city")
    reason = request.POST.get("reason")

    if city and reason:
      return render(
        request,
        "partials/search.html",
        {
          "premade_prompts": choose_topics(reason),
          "city": city,
          "reason": reason,
        },
      )


@login_required
def send_search(request):
  if request.method == "POST":
    return render(
      request,
      "partials/search_results.html",
      {
        "google_maps_api_key": settings.GOOGLE_PLACES_API_KEY,
        "loading": True,
      },
    )


@login_required
def search_response(request, city, reason, topic):
  if request.method == "POST":
    try:
      prompt = f"I want to learn more about {topic} in {city}"
      response = chatbot_response(request, prompt)
      # response = "Test Response"
      additional_data = None
      text = response["response"]

      if isinstance(response, JsonResponse):
        message = Message(
          is_from_user=False,
          text="An error occurred processing your request. Please refresh and try again.",
        )

        return render(
          request,
          "partials/search_results.html",
          {
            "loading": False,
            "error": message.text,
          },
        )
      else:
        locations = []
        if "data" in response:
          additional_data = response["data"]

          if "hotels" in response["data"]:
            locations = [
              {"lat": hotel["details"]["location"]["lat"], "lng": hotel["details"]["location"]["lng"]}
              for hotel in response["data"]["hotels"]
              if "details" in hotel and "location" in hotel["details"]
            ]

        if not locations:
          locations = [
            {"lat": -33.8688, "lng": 151.2093},
          ]

        return render(
          request,
          "partials/search_results.html",
          {
            "error": "",
            "loading": False,
            "text": text,
            "additional_data": additional_data,
            "locations": json.dumps(locations),
            "google_maps_api_key": settings.GOOGLE_PLACES_API_KEY,
          },
        )
    except Exception as e:
      print("Error:", e)
      return JsonResponse({"error": "An error occurred processing your request."}, status=500)

  # return redirect("chatbot")
