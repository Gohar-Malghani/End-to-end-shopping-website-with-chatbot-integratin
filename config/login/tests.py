from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


class LoginFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='alex',
            password='correct-horse-battery',
        )
        self.login_url = reverse('login_page')
        self.shop_url = reverse('shop_home')
        self.chat_url = reverse('page_chat')

    def test_login_page_renders(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in to your account')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, 'shop-chat-launcher')
        self.assertContains(response, 'shop-logo.svg')
        self.assertContains(response, 'Sign in to chat')
        self.assertContains(response, 'shop-chat.js')

    def test_authenticated_user_can_chat_from_floating_widget(self):
        self.client.force_login(self.user)

        response = self.client.get(self.shop_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'shop-chat-launcher')
        self.assertContains(response, 'shop-chat-form')
        self.assertNotContains(response, 'shop-chat-signin')

    def test_login_page_is_available_when_already_authenticated(self):
        self.client.force_login(self.user)

        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in to your account')
        self.assertContains(response, 'Continue to chat')

    def test_login_can_switch_to_another_account(self):
        other_user = get_user_model().objects.create_user(
            username='sam',
            password='another-correct-password',
        )
        self.client.force_login(self.user)

        response = self.client.post(
            self.login_url,
            {'username': 'sam', 'password': 'another-correct-password'},
        )

        self.assertRedirects(response, self.shop_url)
        self.assertEqual(response.wsgi_request.user, other_user)

    def test_valid_credentials_sign_user_in(self):
        response = self.client.post(
            self.login_url,
            {'username': 'alex', 'password': 'correct-horse-battery'},
        )

        self.assertRedirects(response, self.shop_url)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_invalid_credentials_show_error(self):
        response = self.client.post(
            self.login_url,
            {'username': 'alex', 'password': 'wrong-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            self.login_url,
            {
                'username': 'alex',
                'password': 'correct-horse-battery',
                'next': 'https://example.com/',
            },
        )

        self.assertRedirects(response, self.shop_url)

    def test_chat_requires_authentication(self):
        response = self.client.get(self.chat_url)

        self.assertRedirects(
            response,
            f'{self.login_url}?next={self.chat_url}',
        )

    def test_chat_api_requires_authentication(self):
        response = self.client.post(
            reverse('chat_api'),
            data='{"question": "Help"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(self.login_url))

    def test_logout_requires_post_and_ends_session(self):
        self.client.force_login(self.user)

        get_response = self.client.get(reverse('logout_user'))
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(get_response.wsgi_request.user.is_authenticated)

        post_response = self.client.post(reverse('logout_user'))
        self.assertRedirects(post_response, self.login_url)
        self.assertFalse(post_response.wsgi_request.user.is_authenticated)


class RegistrationFlowTests(TestCase):
    def setUp(self):
        self.register_url = reverse('register_page')
        self.login_url = reverse('login_page')

    def test_register_page_renders(self):
        response = self.client.get(self.register_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create your account')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, 'shop-chat-launcher')
        self.assertContains(response, 'shop-logo.svg')
        self.assertContains(response, 'shop-chat.js')

    def test_homepage_shows_the_shop(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ShopNest')
        self.assertContains(response, 'Cloudstep Runner')

    def test_homepage_shows_shop_for_authenticated_users(self):
        user = get_user_model().objects.create_user(
            username='signed-in-user',
            password='correct-horse-battery',
        )
        self.client.force_login(user)

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cloudstep Runner')
        self.assertContains(response, 'Hi, signed-in-user')
        self.assertContains(response, 'Hi signed-in-user!')
        self.assertContains(response, 'shop-chat-form')

    def test_valid_registration_creates_user_and_redirects_to_login(self):
        response = self.client.post(
            self.register_url,
            {
                'username': 'new-user',
                'email': 'new-user@example.com',
                'password': 'Different-strong-password-928!',
                'confirm_password': 'Different-strong-password-928!',
            },
        )

        self.assertRedirects(response, self.login_url)
        user = get_user_model().objects.get(username='new-user')
        self.assertEqual(user.email, 'new-user@example.com')
        self.assertTrue(user.check_password('Different-strong-password-928!'))

    def test_registration_rejects_password_mismatch(self):
        response = self.client.post(
            self.register_url,
            {
                'username': 'new-user',
                'email': 'new-user@example.com',
                'password': 'Different-strong-password-928!',
                'confirm_password': 'Another-strong-password-928!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match.')
        self.assertFalse(
            get_user_model().objects.filter(username='new-user').exists()
        )
