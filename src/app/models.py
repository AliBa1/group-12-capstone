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

class Preferences(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  house_property_type = models.CharField(max_length=100, null=True, blank=True)

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
    google_rating = models.FloatField(null=True, blank=True)
    photo_references = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.iata_code if self.iata_code else ''}"

class Flight(models.Model):
    flight_iata_num = models.CharField(max_length=10, null=True)
    flight_date = models.DateField(max_length=10, null=True)
    airline = models.CharField(max_length=50, null=True)
    airline_code = models.CharField(max_length=3, null=True)
    departure_city = models.CharField(max_length=50, null=True)
    departure_time = models.TimeField(max_length=20, null=True)
    departure_terminal = models.CharField(max_length=2, null=True)
    departure_gate = models.CharField(max_length=3, null=True)
    arrival_city = models.CharField(max_length=50, null=True)
    arrival_time = models.TimeField(max_length=20, null=True)
    arrival_terminal = models.CharField(max_length=2, null=True)
    arrival_gate = models.CharField(max_length=3, null=True)
    flight_price = models.CharField(max_length=15, null=True)

   
class ListingAgent(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField()

    def __str__(self):
        return self.name

class ListingOffice(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField()

    def __str__(self):
        return self.name

class Property(models.Model):
    formatted_address = models.CharField(max_length=255)
    latitude = models.FloatField(default=None)
    longitude = models.FloatField(default=None)
    property_type = models.CharField(max_length=255)
    bedrooms = models.IntegerField()
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1)
    square_footage = models.IntegerField()
    lot_size = models.IntegerField()
    year_built = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    listing_type = models.CharField(max_length=50)
    days_on_market = models.IntegerField()
    mls_name = models.CharField(max_length=255)
    mls_number = models.CharField(max_length=255)
    listing_agent = models.ForeignKey(ListingAgent, on_delete=models.CASCADE)
    listing_office = models.ForeignKey(ListingOffice, on_delete=models.CASCADE)
    house_rating = models.CharField(max_length=5)

    def __str__(self):
      return self.formatted_address

class PropertyHistory(models.Model):
    property = models.ForeignKey(Property, related_name="history", on_delete=models.CASCADE)
    date = models.DateField()
    event = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    listing_type = models.CharField(max_length=50)
    listed_date = models.DateTimeField()
    removed_date = models.DateTimeField(null=True, blank=True)
    days_on_market = models.IntegerField()

    def __str__(self):
        return f"{self.date} - {self.event}"