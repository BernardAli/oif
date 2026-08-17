import re

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import User


EMAIL = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=EMAIL)
class SignupEmailTest(TestCase):
    def test_signup_creates_a_pending_account_and_does_not_sign_in(self):
        response = self.client.post(reverse("accounts:signup"), {
            "first_name": "Ama", "last_name": "Mensah",
            "username": "ama.member", "email": "ama@example.com",
            "phone": "0200000000",
            "password1": "A-secure-test-password-123",
            "password2": "A-secure-test-password-123",
        })
        # New members are not signed in - they must be approved first.
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

        user = User.objects.get(username="ama.member")
        self.assertFalse(user.is_active)
        self.assertEqual(user.role, "MEMBER")

        # One email to the new member, one internal notification to staff.
        self.assertEqual(len(mail.outbox), 2)
        member_email = next(m for m in mail.outbox if m.to == ["ama@example.com"])
        self.assertIn("pending review", member_email.body)
        self.assertNotIn("A-secure-test-password-123", member_email.body)
        staff_email = next(m for m in mail.outbox if m != member_email)
        self.assertIn("pending approval", staff_email.subject)

    def test_pending_account_cannot_sign_in_until_approved(self):
        self.client.post(reverse("accounts:signup"), {
            "first_name": "Kofi", "last_name": "Boateng",
            "username": "kofi.pending", "email": "kofi@example.com",
            "phone": "0200000001",
            "password1": "Another-secure-pass-123",
            "password2": "Another-secure-pass-123",
        })

        response = self.client.post(reverse("accounts:login"), {
            "username": "kofi.pending", "password": "Another-secure-pass-123",
        })
        self.assertEqual(response.status_code, 200)  # re-rendered with an error, not logged in
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "pending approval")

        user = User.objects.get(username="kofi.pending")
        user.is_active = True
        user.save(update_fields=["is_active"])

        response = self.client.post(reverse("accounts:login"), {
            "username": "kofi.pending", "password": "Another-secure-pass-123",
        })
        self.assertRedirects(response, reverse("dashboard:home"))
        self.assertIn("_auth_user_id", self.client.session)


@override_settings(EMAIL_BACKEND=EMAIL)
class PasswordResetFlowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reset_user",
            email="reset@example.com",
            password="old-pass-12345",
        )

    def test_password_reset_sends_email_and_accepts_token(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "reset@example.com"},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)

        match = re.search(r"/accounts/reset/[^/]+/[^/]+/", mail.outbox[0].body)
        self.assertIsNotNone(match)

        reset_url = match.group(0)
        response = self.client.get(reset_url)
        self.assertEqual(response.status_code, 302)

        session_url = response["Location"]
        response = self.client.post(
            session_url,
            {
                "new_password1": "new-pass-12345",
                "new_password2": "new-pass-12345",
            },
        )
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-pass-12345"))


@override_settings(MEDIA_ROOT="/tmp/oif_profile_test_media")
class ProfilePageTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile_user",
            email="profile@example.com",
            password="profile-pass-12345",
            first_name="Profile",
            last_name="User",
        )

    def test_profile_page_uploads_and_displays_avatar(self):
        self.client.login(username="profile_user", password="profile-pass-12345")
        avatar = SimpleUploadedFile(
            "avatar.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00\xff\xff\xff,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )

        response = self.client.post(reverse("accounts:profile"), data={
            "first_name": "Profile",
            "last_name": "User",
            "email": "profile@example.com",
            "phone": "+233 000 000 000",
            "title": "Program Lead",
            "location": "Accra, Ghana",
            "avatar": avatar,
            "bio": "Building excellent programs.",
            "is_public_profile": "on",
        })
        self.assertRedirects(response, reverse("accounts:profile"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar.name.startswith("avatars/avatar"))
        self.assertTrue(self.user.is_public_profile)

        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "profile-avatar-img")
        self.assertContains(response, self.user.avatar.url)
