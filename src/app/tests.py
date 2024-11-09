from django.test import TestCase, Client
from django.urls import reverse
from app.models import Conversation, Message
from user.models import User
from django.contrib.messages import get_messages


class ConversationTests(TestCase):
  def setUp(self):
    self.user = User.objects.create_user(username="t@t.com", email="t@t.com", password="asdfghjkl")
    self.c1 = Conversation.objects.create(title="Test C1", city="Miami, FL", reason="Moving", user=self.user)
    self.m1 = Message.objects.create(is_from_user=True, text="Hello Embarkr", conversation=self.c1)
    self.client = Client()

  def test_fetch_conversation_unauthenticated(self):
    # Test access without logging in
    url = reverse("fetch_conversation", args=[self.c1.id])
    response = self.client.get(url)
    self.assertEqual(response.status_code, 302)

  def test_fetch_conversation(self):
    Message.objects.create(is_from_user=False, text="Test bot response", conversation=self.c1)
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("fetch_conversation", args=[self.c1.id])
    response = self.client.get(url)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, "partials/chat.html")
    self.assertIn("chat_messages", response.context)
    self.assertEqual(len(Message.objects.all()), 2)
    self.assertEqual(len(response.context["chat_messages"]), 2)
    self.assertEqual(response.context["chat_messages"][0].is_from_user, True)
    self.assertEqual(response.context["chat_messages"][0].text, "Hello Embarkr")
    self.assertEqual(response.context["chat_messages"][0].conversation, self.c1)
    self.assertLess(response.context["chat_messages"][0].timestamp, response.context["chat_messages"][1].timestamp)
    self.assertEqual(response.context["conversation_id"], self.c1.id)
    self.assertFalse(response.context["bot_typing"])
    self.assertEqual(response.context["prompt"], None)

  def test_new_conversation(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("new_conversation")
    # space is to test if it's being trimed
    response = self.client.post(url, {"title": "Testing New Conversation ", "city": "Miami, FL", "reason": "Moving"})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    messages = list(get_messages(response.wsgi_request))
    self.assertEqual(len(messages), 0)
    self.assertTrue(
      Conversation.objects.filter(
        title="Testing New Conversation", city="Miami, FL", reason="Moving", user=self.user
      ).exists()
    )

  def test_new_conversation_title_empty(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("new_conversation")
    response = self.client.post(url, {"title": "", "city": "Miami, FL", "reason": "Moving"})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    messages = list(get_messages(response.wsgi_request))
    self.assertFalse(Conversation.objects.filter(title="", city="Miami, FL", reason="Moving", user=self.user).exists())
    self.assertGreater(len(messages), 0)
    self.assertEqual("The title can not be empty", str(messages[0]))

  def test_new_conversation_long_title(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("new_conversation")
    response = self.client.post(
      url,
      {
        "title": "Testing New Conversation but Very Very Long so That There is a Limit on the size of Titles",
        "city": "Miami, FL",
        "reason": "Moving",
      },
    )

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    self.assertFalse(
      Conversation.objects.filter(
        title="Testing New Conversation but Very Very Long so That There is a Limit on the size of Titles",
        city="Miami, FL",
        reason="Moving",
        user=self.user,
      ).exists()
    )
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("The title is too long (max characters: 60)", str(messages[0]))

  def test_new_conversation_title_exists(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    self.assertTrue(Conversation.objects.filter(title="Test C1", city="Miami, FL", reason="Moving", user=self.user).exists())
    url = reverse("new_conversation")
    response = self.client.post(url, {"title": "Test C1"})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("A conversation with this title already exists", str(messages[0]))
    self.assertEqual(len(Conversation.objects.filter(title="Test C1", city="Miami, FL", reason="Moving", user=self.user)), 1)

  def test_rename_conversation(self):
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("rename_conversation", args=[self.c1.id])
    response = self.client.post(url, {"new-title": "Renamed Test C1"})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    messages = list(get_messages(response.wsgi_request))
    self.assertEqual(len(messages), 0)
    self.assertTrue(Conversation.objects.filter(title="Renamed Test C1", user=self.user).exists())
    self.assertEqual(len(Conversation.objects.all()), 1)

  def test_rename_conversation_title_exists(self):
    Conversation.objects.create(title="Test C2", user=self.user)
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("rename_conversation", args=[self.c1.id])
    response = self.client.post(url, {"new-title": "Test C2"})

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    self.assertEqual(len(Conversation.objects.all()), 2)
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("A conversation with this title already exists", str(messages[0]))
    self.assertEqual(len(Conversation.objects.filter(title="Test C2", user=self.user)), 1)

  def test_delete_conversation(self):
    test_conversation = Conversation.objects.create(title="Test C2", user=self.user)
    self.assertTrue(Conversation.objects.filter(title="Test C2", user=self.user).exists())
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("delete_conversation", args=[test_conversation.id])
    response = self.client.post(url)

    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, reverse("explore"))
    messages = list(get_messages(response.wsgi_request))
    self.assertEqual(len(messages), 0)
    self.assertEqual(len(Conversation.objects.all()), 1)
    self.assertFalse(Conversation.objects.filter(title="Test C2", user=self.user).exists())

  def test_delete_conversation_not_exist(self):
    self.assertFalse(Conversation.objects.filter(title="Test C2", user=self.user).exists())
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("delete_conversation", args=[123123123])
    response = self.client.post(url)

    self.assertEqual(response.status_code, 404)
    self.assertEqual(len(Conversation.objects.all()), 1)

  def test_send_prompt(self):
    self.assertEqual(len(Message.objects.all()), 1)
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("send_prompt", args=[self.c1.id])
    response = self.client.post(url, {"prompt": "User sent this prompt"})

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, "partials/chat.html")
    messages = list(get_messages(response.wsgi_request))
    self.assertEqual(len(messages), 0)

    self.assertTrue(Message.objects.filter(text="User sent this prompt").exists())
    self.assertTrue(Message.objects.get(text="User sent this prompt").is_from_user)
    self.assertEqual(Message.objects.get(text="User sent this prompt").conversation, self.c1)
    self.assertEqual(len(Message.objects.filter(text="User sent this prompt")), 1)

    self.assertEqual(len(response.context["chat_messages"]), 2)
    self.assertLess(response.context["chat_messages"][0].timestamp, response.context["chat_messages"][1].timestamp)
    self.assertEqual(response.context["conversation_id"], self.c1.id)
    self.assertTrue(response.context["bot_typing"])
    self.assertEqual(response.context["prompt"], "User sent this prompt")

  def test_send_premade_prompt(self):
    self.assertEqual(len(Message.objects.all()), 1)
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("send_prompt", args=[self.c1.id])
    response = self.client.post(url, {"pre-made-prompt": "Schools"})
    city = self.c1.city

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, "partials/chat.html")
    messages = list(get_messages(response.wsgi_request))
    self.assertEqual(len(messages), 0)

    self.assertTrue(Message.objects.filter(text="I want to learn more about schools in " + city).exists())
    self.assertTrue(Message.objects.get(text="I want to learn more about schools in " + city).is_from_user)
    self.assertEqual(
      Message.objects.get(text="I want to learn more about schools in " + city).conversation, self.c1
    )
    self.assertEqual(len(Message.objects.filter(text="I want to learn more about schools in " + city)), 1)

    self.assertEqual(len(response.context["chat_messages"]), 2)
    self.assertLess(response.context["chat_messages"][0].timestamp, response.context["chat_messages"][1].timestamp)
    self.assertEqual(response.context["conversation_id"], self.c1.id)
    self.assertTrue(response.context["bot_typing"])
    self.assertEqual(response.context["prompt"], "I want to learn more about schools in " + city)

  def test_send_response(self):
    test_message = Message.objects.create(is_from_user=True, text="User sent this prompt", conversation=self.c1)
    self.assertEqual(len(Message.objects.all()), 2)
    self.client.login(username="t@t.com", password="asdfghjkl")
    url = reverse("send_response", args=[self.c1.id, test_message.text])
    response = self.client.post(url)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, "partials/chat.html")
    messages = list(get_messages(response.wsgi_request))
    self.assertEqual(len(messages), 0)

    self.assertEqual(len(Message.objects.all()), 3)
    self.assertTrue(Message.objects.filter(is_from_user=False).exists())
    self.assertEqual(len(Message.objects.filter(is_from_user=False)), 1)

    self.assertEqual(len(response.context["chat_messages"]), 3)
    self.assertLess(response.context["chat_messages"][1].timestamp, response.context["chat_messages"][2].timestamp)
    self.assertEqual(response.context["conversation_id"], self.c1.id)
    self.assertFalse(response.context["bot_typing"])
    self.assertEqual(response.context["prompt"], None)
