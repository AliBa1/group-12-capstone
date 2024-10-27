from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.contrib.messages import get_messages
from django.contrib.auth.models import User


class UserTests(TestCase):
  def setUp(self):
    self.user = User.objects.create_user(username="test2@test.com", email="test2@test.com", password="as12as12")
    # self.client = Client(enforce_csrf_checks=True)
    self.client = Client()

  def test_login_success(self):
    response = self.client.post("/login/", {"email": "test2@test.com", "password": "as12as12"}, follow=True)
    self.assertEqual(response.status_code, 200)
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("You have been logged in.", str(messages[0]))

  def test_login_wrong_email(self):
    response = self.client.post("/login/", {"email": "t@test.com", "password": "as12as12"}, follow=True)
    self.assertEqual(response.status_code, 200)
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("Incorrect email or password", str(messages[0]))

  def test_login_wrong_password(self):
    response = self.client.post("/login/", {"email": "test2@test.com", "password": "wrongpassword"}, follow=True)
    self.assertEqual(response.status_code, 200)
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("Incorrect email or password", str(messages[0]))
  
  def test_register_success(self):
    response = self.client.post("/register/", {"email": "test3@test.com", "password": "asd123asd123", "confirm-password": "asd123asd123"}, follow=True)
    self.assertEqual(response.status_code, 200)
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("Account created under test3@test.com", str(messages[0]))

  def test_register_empty_field(self):
    response = self.client.post("/register/", {"email": "", "password": "asd123asd123", "confirm-password": "asd123asd123"}, follow=True)
    self.assertEqual(response.status_code, 200)
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("Fields cannot be left empty", str(messages[0]))

  def test_register_existing_account(self):
    response = self.client.post("/register/", {"email": "test2@test.com", "password": "asd123asd123", "confirm-password": "asd123asd123"}, follow=True)
    self.assertEqual(response.status_code, 200)
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("An account with this email exists", str(messages[0]))

  def test_register_passwords_not_matching(self):
    response = self.client.post("/register/", {"email": "test3@test.com", "password": "asd123asd123asd123", "confirm-password": "asd123asd123"}, follow=True)
    self.assertEqual(response.status_code, 200)
    messages = list(get_messages(response.wsgi_request))
    self.assertGreater(len(messages), 0)
    self.assertEqual("Passwords don't match", str(messages[0]))
