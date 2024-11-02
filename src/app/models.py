from django.db import models


# Create your models here.
class Conversation(models.Model):
  title = models.CharField(max_length=250, unique=True)
  created_at = models.DateTimeField(auto_now_add=True)
  # folder = models.


class Message(models.Model):
  timestamp = models.DateTimeField(auto_now_add=True)
  is_from_user = models.BooleanField(default=False)
  text = models.TextField()
  conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
  # map = models.
  # api_data = models.
