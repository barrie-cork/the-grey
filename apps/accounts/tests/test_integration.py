from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class AuthenticationIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_complete_signup_login_flow(self):
        """Test complete signup → login flow"""
        # 1. Sign up
        signup_url = reverse("accounts:signup")
        response = self.client.post(
            signup_url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "testpass123!",
                "password2": "testpass123!",
                "first_name": "John",
                "last_name": "Doe",
            },
        )
        self.assertEqual(response.status_code, 302)

        # 2. Verify user is created and logged in
        self.assertTrue(User.objects.filter(username="newuser").exists())
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)  # No redirect, user is logged in

        # 3. Logout
        self.client.logout()

        # 4. Login with username
        login_url = reverse("accounts:login")
        response = self.client.post(
            login_url, {"username": "newuser", "password": "testpass123!"}
        )
        self.assertEqual(response.status_code, 302)

        # 5. Verify logged in
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)

    def test_profile_update_after_login(self):
        """Test profile update after login"""
        # Create user
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Login
        self.client.login(username="testuser", password="testpass123")

        # Update profile
        profile_url = reverse("accounts:profile")
        response = self.client.post(
            profile_url,
            {
                "email": "updated@example.com",
                "first_name": "Updated",
                "last_name": "User",
            },
        )
        self.assertEqual(response.status_code, 302)

        # Verify update
        user.refresh_from_db()
        self.assertEqual(user.email, "updated@example.com")
        self.assertEqual(user.first_name, "Updated")
        self.assertEqual(user.last_name, "User")

    def test_password_reset_email_flow(self):
        """Test password reset email flow"""
        # Create user
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="oldpass123"
        )

        # Request password reset
        reset_url = reverse("accounts:password_reset")
        response = self.client.post(reset_url, {"email": "test@example.com"})
        self.assertEqual(response.status_code, 302)

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("test@example.com", mail.outbox[0].to)
        self.assertIn("password reset", mail.outbox[0].subject.lower())

        # Extract reset link from email
        email_body = mail.outbox[0].body
        self.assertIn("accounts/reset/", email_body)

    def test_redirect_chains(self):
        """Test redirect chains for protected views"""
        # Try to access profile without login
        profile_url = reverse("accounts:profile")
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 302)
        # Should redirect to login with next parameter
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertIn("next=", response.url)

        # Login and verify redirect back to profile
        response = self.client.post(
            reverse("accounts:login") + f"?next={profile_url}",
            {"username": "testuser", "password": "testpass123!"},
        )
        # Note: Need to create the user first
        user = User.objects.create_user(username="testuser", password="testpass123!")
        response = self.client.post(
            reverse("accounts:login") + f"?next={profile_url}",
            {"username": "testuser", "password": "testpass123!"},
            follow=True,
        )
        # Should end up at profile page
        self.assertContains(response, "Edit Profile")

    def test_session_expiry_behavior(self):
        """Test session expiry settings"""
        # Create and login user
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

        # Check session exists
        self.assertIn("_auth_user_id", self.client.session)

        # Session should have correct expiry (24 hours = 86400 seconds)
        self.assertEqual(self.client.session.get_expiry_age(), 86400)
