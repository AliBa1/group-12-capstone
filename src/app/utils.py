
from app.constants import premade_moving, premade_travel, topics_moving, topics_travel
from django.contrib import messages
from app.models import Conversation

# helper functions
def choose_premade_prompts(conversation):
  if conversation.reason == "Travel":
    return premade_travel
  else:
    return premade_moving
  
def choose_topics(reason):
  if reason == "Travel":
    return topics_travel
  else:
    return topics_moving
  
def get_all_topics():
  return topics_moving + topics_travel

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