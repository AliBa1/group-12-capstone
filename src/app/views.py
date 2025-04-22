import os
import json
import joblib
import requests
import googlemaps
import pandas as pd
from openai import OpenAI
from django.conf import settings
from app.constants import cities
from app.models import Conversation, Message, Preferences
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_http_methods
from app.utils import choose_premade_prompts, choose_topics, is_title_valid, get_all_topics
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
          hotels = data.get("hotels", [])
          locations = [
            {"lat": hotel["details"]["location"]["lat"], "lng": hotel["details"]["location"]["lng"]}
            for hotel in hotels
            if "details" in hotel and "location" in hotel["details"]
          ]
        elif "places" in data:
          places = data.get("places", [])
          locations = [
            {"lat": place["details"]["latitude"], "lng": place["details"]["longitude"]}
            for place in places
            if "details" in place and "latitude" in place["details"] and "longitude" in place["details"]
          ]
          print("Locations: ", places[0])
        elif "apartments" in data or "houses" in data:
          property_list = data.get("apartments", []) or data.get("houses", [])
          locations = [
            {"lat": prop["latitude"], "lng": prop["longitude"]}
            for prop in property_list
            if "latitude" in prop and "longitude" in prop
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
  flights = []
  houses = []
  apartments = []
  latest_message = (
    Message.objects.filter(
      conversation=conversation,
      is_from_user=False,
      additional_data__isnull=False,
    )
    .order_by("-timestamp")
    .first()
  )

  if latest_message and latest_message.additional_data:
    try:
      if isinstance(latest_message.additional_data, str):
        data = json.loads(latest_message.additional_data)
      else:
        data = latest_message.additional_data

      if "hotels" in data:
        locations = [
          {"lat": hotel["details"]["location"]["lat"], "lng": hotel["details"]["location"]["lng"]}
          for hotel in data["hotels"]
          if "details" in hotel and "location" in hotel["details"]
        ]
      if "places" in data:
        locations = [
          {"lat": place["details"]["latitude"], "lng": place["details"]["longitude"]}
          for place in data["places"]
            if "details" in place and "latitude" in place["details"] and "longitude" in place["details"]
        ]
      if "flights" in data:
        flights = data["flights"]
      if "houses" in data:
        houses = data["houses"]
        locations = [
          {"lat": house["latitude"], "lng": house["longitude"]}
          for house in data["houses"]
          if "latitude" in house and "longitude" in house
        ]
      if "apartments" in data:
        apartments = data["apartments"]
        locations = [
          {"lat": apartment["latitude"], "lng": apartment["longitude"]}
          for apartment in data["apartments"]
          if "latitude" in apartment and "longitude" in apartment
        ]
    except json.JSONDecodeError as e:
      print(f"Error decoding JSON: {e}")
    except Exception as e:
      print(f"Error processing additional_data: {e}")
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
      "flights": flights,
      "houses": houses,
      "apartments": apartments,
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
    # new_city = request.POST.get("updated-city")
    # new_reason = request.POST.get("updated-reason")

    is_valid = is_title_valid(request, new_title)

    if is_valid:
      conversation.title = new_title
      # conversation.city = new_city
      # conversation.reason = new_reason
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
      prompt = f"Find me {premade_prompt} in {conversation.city}"

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

        flights = []
        locations = []
        houses = []
        apartments = []
        if "data" in response:
          try:
            raw = response['data']
            def normalize(o):
              # 1) If it’s a dict or list, recurse
              if isinstance(o, dict):
                  return {k: normalize(v) for k, v in o.items()}
              if isinstance(o, (list, tuple)):
                  return [normalize(v) for v in o]

              # 2) If it has to_dict(), use that
              if hasattr(o, "to_dict") and callable(o.to_dict):
                  return normalize(o.to_dict())

              # 3) If it looks like LocalizedText (has .text.value), unwrap
              text_attr = getattr(o, "text", None)
              if text_attr and hasattr(text_attr, "value"):
                  return text_attr.value

              # 4) Primitives pass through
              if isinstance(o, (str, int, float, bool)) or o is None:
                  return o

              # 5) Fallback: convert to string
              return str(o)

            data = normalize(raw)
            # if isinstance(response["data"], str):
            #   parts = response["data"].split(",", 1)
            #   if len(parts) > 1:
            #     raw_json = parts[1].strip()
            #     raw_json = raw_json.replace("'", '"')
            #     data = json.loads(raw_json)
            #   else:
            #     raise ValueError("No dictionary part found in the data string")
            # else:
            #   data = response["data"]

            message.additional_data = data
            message.save()

            if "flights" in data:
              flights = data.get("flights", [])
              message.additional_data = {"flights": flights, "type": "flight_search"}
              message.save()

            if "houses" in data:
              houses = data.get("houses", [])
              message.additional_data = {"houses": houses, "type": "house_search"}
              message.save()
            if "apartments" in data:
              apartments = data.get("apartments", [])
              message.additional_data = {"apartments": apartments, "type": "apartment_search"}
              message.save()

          except (json.JSONDecodeError, TypeError) as e:
            print(f"Error decoding response['data']: {e}")
          if "hotels" in response["data"]:
            locations = [
              {"lat": hotel["details"]["location"]["lat"], "lng": hotel["details"]["location"]["lng"]}
              for hotel in response["data"]["hotels"]
              if "details" in hotel and "location" in hotel["details"]
            ]
          elif "places" in data:
            locations = [
              {"lat": place["details"]["latitude"], "lng": place["details"]["longitude"]}
              for place in response["data"]["places"]
              if "details" in place and "latitude" in place["details"] and "longitude" in place["details"]
            ]
          elif "houses" in response["data"]:
            locations = [
              {"lat": house["latitude"], "lng": house["longitude"]}
              for house in response["data"]["houses"]
              if "latitude" in house and "longitude" in house
            ]
          elif "apartments" in response["data"]:
            locations = [
              {"lat": apartment["latitude"], "lng": apartment["longitude"]}
              for apartment in response["data"]["apartments"]
              if "latitude" in apartment and "longitude" in apartment
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
          "flights": flights,
          "houses": houses,
          "apartments": apartments,
        },
      )
    except Exception as e:
      print("Error in send_response:", e)
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
      print(f"Strategy: {strategy}")
      if strategy:
        conversation_id = request.POST.get("conversation_id")
        city = None
        if conversation_id:
          conversation = get_object_or_404(Conversation, id=conversation_id)
          city = conversation.city

        print("Strategy: ", strategy)
        strategy_response = strategy.process_query(prompt=prompt, city=city, user=request.user)
        print("Response: ", strategy_response)
        if strategy_response:
          if isinstance(strategy_response, dict):
            assistant_message = f"{assistant_message} {strategy_response.get('text', '')}"
            return {"response": assistant_message, "data": strategy_response.get("data")}
          else:
            assistant_message = f"{assistant_message} {strategy_response}"
        else:
          return {"response": "An error occured when processing your request. Ask me for something else and I will be happy to help!", "data": {}}

      return {"response": assistant_message}

    except Exception as e:
      print(f"Error in chatbot_response: {str(e)}")
      return JsonResponse({"error": f"Error: {str(e)}"}, status=500)


@require_http_methods(["GET"])
@cache_page(60 * 60 * 24)  # 24 hours
def proxy_hotel_photo(request, photo_reference):
  if not photo_reference:
    return HttpResponseNotFound("No photo reference provided")

  try:
    # gmaps = googlemaps.Client(key=settings.GOOGLE_PLACES_API_KEY)
    base_url = f"https://places.googleapis.com/v1/{photo_reference}/media"

    response = requests.get(base_url, params={"maxWidthPx": 800, "maxHeightPx": 600, "key": settings.GOOGLE_PLACES_API_KEY}, timeout=10)

    if response.status_code == 200:
      return HttpResponse(response.content, content_type=response.headers.get("Content-Type", "image/jpeg"))
    return HttpResponseNotFound("Photo not found")

  except Exception as e:
    print(f"Error proxying photo: {str(e)}")
    return HttpResponseNotFound("Error retrieving photo")


@login_required
def explore_page(request):
  return render(
    request,
    "explore.html",
    {
      "cities": cities,
      "google_maps_api_key": settings.GOOGLE_PLACES_API_KEY,
    },
  )


@login_required
def update_city_reason(request):
  if request.method == "POST":
    city = request.POST.get("city")
    if city:
      return render(
        request,
        "partials/search.html",
        {
          "premade_prompts": get_all_topics(),
          "city": city,
          "cities": cities,
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
def search_response(request, city, topic):
  if request.method == "POST":
    try:
      origin = request.GET.get("origin")
      flight_date = request.GET.get("flight_date")
      property_type = request.POST.get("property_type")

      if topic == "Housing":
        if property_type == "None" or property_type is None:
          prompt = f"Find me houses in {city}"
        else:
          prompt = f"Find me {property_type} properties in {city}"
      elif topic == "Flights" and origin and flight_date:
        prompt = f"Find me flights between {origin} and {city} on {flight_date}"
      else:
        prompt = f"Find me {topic} in {city}"
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
          if "places" in response["data"]:
            locations = [
              {"lat": place["details"]["latitude"], "lng": place["details"]["longitude"]}
              for place in response["data"]["places"]
              if "details" in place and "latitude" in place["details"] and "longitude" in place["details"]
            ]
          # Add once added view on map to apartments
          if "apartments" in response["data"]:
            locations = [
              {"lat": apartment["latitude"], "lng": apartment["longitude"]}
              for apartment in response["data"]["apartments"]
              if "latitude" in apartment and "longitude" in apartment
            ]
          
          if "houses" in response["data"]:
            locations = [
              {"lat": house["latitude"], "lng": house["longitude"]}
              for house in response["data"]["houses"]
              if "latitude" in house and "longitude" in house
            ]
            # print("Locations: ", locations)
            # print("Response: ", response)

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
      print("En rror:", e)
      return JsonResponse({"error": "An error occurred processing your request."}, status=500)


def load_model_and_data():
  try:
    model_path = os.path.join(settings.ML_MODELS_DIR, "random_forest_model.joblib")
    encoder_path = os.path.join(settings.ML_MODELS_DIR, "label_encoder.joblib")
    data_path = os.path.join(settings.ML_MODELS_DIR, "processed_metro_heat_index.csv")

    print(f"Loading model from: {model_path}")

    model = joblib.load(model_path)
    label_encoder = joblib.load(encoder_path)
    data = pd.read_csv(data_path)

    return model, data, label_encoder

  except Exception as e:
    print(f"Error loading model files: {str(e)}")
    raise

def last_heat_index(request):
  try:
    location = request.GET.get("location", "Houston, TX")
    dataset = pd.read_csv(os.path.join(settings.ML_MODELS_DIR, "processed_metro_heat_index.csv"))
    # Get the data for the given location
    location_data = dataset[dataset["RegionName"] == location]

    # Get the last heat index
    location_last_heat_index = location_data.iloc[:, -1].values[0]

    if pd.isna(location_last_heat_index):
      return JsonResponse({"error": "No heat index data available for this location"}, status=404)
    
    return JsonResponse({"location": location, "last_heat_index": float(location_last_heat_index)})

  except Exception as e:
    print(f"Error fetching last heat index: {str(e)}")
    return JsonResponse({"error": "Failed to fetch last heat index", "details": str(e)}, status=500)




def predict_heat_index(request):
  try:
    location = request.GET.get("location", "Houston, TX")
    print(f"Predicting for location: {location}")

    model, data, label_encoder = load_model_and_data()

    state = location.split(", ")[-1].strip()

    try:
      state_encoded = label_encoder.transform([state])[0]
    except ValueError:
      return JsonResponse(
        {"error": f"State '{state}' not found in training data.", "available_states": label_encoder.classes_.tolist()},
        status=400,
      )

    location_data = data[(data["RegionName"] == location) & (data["StateName"] == state_encoded)]

    if location_data.empty:
      return JsonResponse(
        {"error": f"Location not found: {location}", "available_locations": data["RegionName"].unique().tolist()},
        status=404,
      )

    features = location_data[["RegionID", "SizeRank", "StateName"]]
    prediction = model.predict(features)[0]

    return JsonResponse({"location": location, "predicted_heat_index": float(prediction), "state": state})

  except Exception as e:
    print(f"Prediction error: {str(e)}")
    return JsonResponse({"error": "Failed to make prediction", "details": str(e)}, status=500)


@login_required
def update_preferences(request, property_type):
  if request.method == "POST":
    property_type = property_type or request.POST.get("property_type")
    if property_type == "any":
      property_type = None
    preferences, created = Preferences.objects.get_or_create(user=request.user)
    preferences.house_property_type = property_type
    preferences.save()
    return JsonResponse({"status": "success"})
  return JsonResponse({"status": "error"}, status=400)

def cookie_policy(request):
  return render(request, "cookie_policy.html")

def terms_of_use(request):
  return render(request, "terms_of_use.html")
