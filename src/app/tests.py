from django.test import TestCase, Client
from django.urls import reverse
from app.models import Conversation, Message
from user.models import User
from django.contrib.messages import get_messages

class ConversationTests(TestCase):
  def setUp(self):
    self.user = User.objects.create_user(username="t@t.com", email="t@t.com", password="asdfghjkl")
    self.c1 = Conversation.objects.create(title="Test C1", user=self.user)
    self.m1 = Message.objects.create(is_from_user=True, text="Hello Embarkr", conversation=self.c1)
    self.client = Client()

  def test_fetch_conversation_unauthenticated(self):
    # Test access without logging in
    url = reverse("fetch_conversation", args=[self.c1.id])
    response = self.client.get(url)
    self.assertEqual(response.status_code, 302)

  def test_fetch_conversation(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("fetch_conversation", args=[self.c1.id])
    response = self.client.get(url)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, "partials/chat.html")
    self.assertIn("messages", response.context)
    self.assertEqual(len(response.context["messages"]), 1)
    self.assertEqual(response.context["messages"][0].is_from_user, True)
    self.assertEqual(response.context["messages"][0].text, "Hello Embarkr")
    self.assertEqual(response.context["messages"][0].conversation, self.c1)
    self.assertEqual(response.context["conversation_id"], self.c1.id)
    self.assertFalse(response.context["bot_typing"])
  
  def test_new_conversation(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("new_conversation")
    # space is to test if it's being trimed
    response = self.client.post(url, {"title": "Testing New Conversation "})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    self.assertTrue(Conversation.objects.filter(title="Testing New Conversation", user=self.user).exists())

  def test_new_conversation_title_empty(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("new_conversation")
    response = self.client.post(url, {"title": ""})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    messages = list(get_messages(response.wsgi_request))
    self.assertFalse(Conversation.objects.filter(title="", user=self.user).exists())
    self.assertGreater(len(messages), 0)
    self.assertEqual("The title can not be empty", str(messages[0]))
  
  def test_new_conversation_long_title(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("new_conversation")
    response = self.client.post(url, {"title": "Testing New Conversation but Very Very Long so That There is a Limit on the size of Titles"})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    self.assertFalse(Conversation.objects.filter(title="Testing New Conversation but Very Very Long so That There is a Limit on the size of Titles", user=self.user).exists())
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("The title is too long (max characters: 60)", str(messages[0]))

  def test_new_conversation_title_taken(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("new_conversation")
    self.assertTrue(Conversation.objects.filter(title="Test C1", user=self.user).exists())
    response = self.client.post(url, {"title": "Test C1"})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    messages = list(get_messages(response.wsgi_request))
    self.assertTrue(len(Conversation.objects.filter(title="Test C1", user=self.user)) == 1)
    self.assertGreater(len(messages), 0)
    self.assertEqual("A conversation with this title already exists", str(messages[0]))
  
  # def test_rename_conversation(self):
