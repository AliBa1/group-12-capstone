from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField

# Create your models here.
class Conversation(models.Model):
  title = models.CharField(max_length=60, unique=True)
  city = models.CharField(max_length=255)
  reason = models.CharField(max_length=60)
  created_at = models.DateTimeField(auto_now_add=True)
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  # folder = models.


class Message(models.Model):
  timestamp = models.DateTimeField(auto_now_add=True)
  is_from_user = models.BooleanField(default=False)
  text = models.TextField(max_length=2500)
  conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
  additional_data = additional_data = JSONField(null=True, blank=True)
  # map = models.
  # api_data = models.

class Hotel(models.Model):
    hotel_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    chain_code = models.CharField(max_length=10, null=True, blank=True)
    iata_code = models.CharField(max_length=3, null=True, blank=True)
    dupe_id = models.IntegerField(null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    country_code = models.CharField(max_length=2, null=True, blank=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, related_name='hotels')
    google_place_id = models.CharField(max_length=255, null=True, blank=True)
    google_address = models.TextField(null=True, blank=True)
    photo_references = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.iata_code if self.iata_code else ''}"

class Flight(models.Model):
    flight_iata_num = models.CharField(max_length=10, null=True)
    flight_date = models.DateField(max_length=10, null=True)
    airline = models.CharField(max_length=25, null=True)
    airline_code = models.CharField(max_length=3, null=True)
    departure_city = models.CharField(max_length=30, null=True)
    departure_time = models.DateTimeField(max_length=20, null=True)
    departure_terminal = models.CharField(max_length=2, null=True)
    departure_gate = models.CharField(max_length=3, null=True)
    arrival_city = models.CharField(max_length=30, null=True)
    arrival_time = models.DateTimeField(max_length=20, null=True)
    arrival_terminal = models.CharField(max_length=2, null=True)
    arrival_gate = models.CharField(max_length=3, null=True)

   