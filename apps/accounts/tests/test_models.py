from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user_with_uuid(self):
        """Test creating a user generates a UUID primary key"""
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.assertIsNotNone(user.id)
        self.assertEqual(len(str(user.id)), 36)  # UUID length with hyphens

    def test_create_user_with_email(self):
        """Test creating a user with email"""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.assertEqual(user.email, "test@example.com")

    def test_email_unique_constraint(self):
        """Test email uniqueness is enforced"""
        User.objects.create_user(
            username="user1", email="test@example.com", password="pass123"
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username="user2", email="test@example.com", password="pass123"
            )

    def test_email_optional(self):
        """Test email is optional"""
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.assertIsNone(user.email)

    def test_timestamps_auto_populated(self):
        """Test created_at and updated_at are auto-populated"""
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

    def test_db_table_name(self):
        """Test the database table name is 'User'"""
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.assertEqual(user._meta.db_table, "User")

    def test_date_joined_is_none(self):
        """Test date_joined field is hidden"""
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.assertIsNone(user.date_joined)

    def test_user_string_representation(self):
        """Test the string representation of User"""
        user = User.objects.create_user(username="testuser", password="testpass123")
        self.assertEqual(str(user), "testuser")

    def test_create_superuser(self):
        """Test creating a superuser"""
        admin = User.objects.create_superuser(username="admin", password="adminpass123")
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_active)
