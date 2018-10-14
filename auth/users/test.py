from django.contrib.auth import get_user_model, authenticate
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from rest_framework_jwt.settings import api_settings


User = get_user_model()


USER_VASCO = {
    'username': 'VasmV',
    'email': 'vasco@foothub.com',
    'password': 'verystrong1'
}

USER_JOAO = {
    'username': 'Jefe',
    'email': 'joao@foothub.com',
    'password': 'verystrong2'
}


class TestUserBackend(TestCase):
    def setUp(self):
        User.objects.create_user(**USER_VASCO)
        User.objects.create_user(**USER_JOAO)

    def test_no_username_fail(self):
        self.assertIsNone(authenticate())

    def test_no_user_fail(self):
        self.assertIsNone(authenticate(username='bad_username'))

    def test_username_authentication_fail(self):
        self.assertIsNone(authenticate(username=USER_VASCO['username'], password=USER_JOAO['password']))

    def test_username_authentication_success(self):
        self.assertIsNotNone(authenticate(username=USER_VASCO['username'], password=USER_VASCO['password']))

    def test_email_authentication_fail(self):
        self.assertIsNone(authenticate(username=USER_VASCO['email'], password=USER_JOAO['password']))

    def test_email_authentication_success(self):
        self.assertIsNotNone(authenticate(username=USER_VASCO['email'], password=USER_VASCO['password']))


class TestUserManager(TestCase):
    def test_create_user_success(self):
        self.assertEqual(User.objects.count(), 0)

        user = User.objects.create_user(**USER_VASCO)

        self.assertEqual(User.objects.count(), 1)

        self.assertEqual(user.username, USER_VASCO['username'])
        self.assertEqual(user.email, USER_VASCO['email'])
        self.assertTrue(user.check_password(USER_VASCO['password']))


class TestUserCreationApi(APITestCase):
    URL = '/create-user'
    CONTENT_TYPE = 'json'

    def setUp(self):
        self.user_vasco = User.objects.create_user(**USER_VASCO)

    def test_create_user_400_invalid(self):
        self.assertEqual(User.objects.count(), 1)
        bad_user = {
            'username': 'username@foothub.com',
            'email': 'email@foothub.com',
            'password': 'legitpw123',
        }

        response = self.client.post(self.URL, bad_user, format=self.CONTENT_TYPE)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_create_user_400_forbidden(self):
        self.assertEqual(User.objects.count(), 1)
        bad_user = dict(USER_VASCO)
        bad_user['username'] = 'me'

        response = self.client.post(self.URL, bad_user, format=self.CONTENT_TYPE)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_create_user_400_existing(self):
        self.assertEqual(User.objects.count(), 1)

        response = self.client.post(self.URL, USER_VASCO, format=self.CONTENT_TYPE)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_create_user_200(self):
        self.assertEqual(User.objects.count(), 1)

        response = self.client.post(self.URL, USER_JOAO, format=self.CONTENT_TYPE)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(User.objects.count(), 2)

        user_joao = User.objects.get(username=USER_JOAO['username'])

        self.assertEqual(user_joao.username, USER_JOAO['username'])
        self.assertEqual(user_joao.email, USER_JOAO['email'])
        self.assertTrue(user_joao.check_password(USER_JOAO['password']))


class TestUsersApi(APITestCase):
    URL = '/users'
    CONTENT_TYPE = 'json'

    @classmethod
    def instance_url(cls, username: str):
        return f'{cls.URL}/{username}'

    def setUp(self):
        user_vasco = User.objects.create_user(**USER_VASCO)

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user_vasco)
        token = jwt_encode_handler(payload)

        self.kwargs = {
            'HTTP_AUTHORIZATION': f'JWT {token}',
            'format': self.CONTENT_TYPE
        }

        User.objects.create_user(**USER_JOAO)

    def test_list_405(self):
        response = self.client.get(self.URL, **self.kwargs)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_405(self):
        response = self.client.post(self.instance_url(USER_VASCO['username']), data={}, **self.kwargs)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_405(self):
        response = self.client.put(self.instance_url(USER_VASCO['username']), data={}, **self.kwargs)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_retrieve_401(self):
        response = self.client.get(self.instance_url(USER_VASCO['username']), format=self.CONTENT_TYPE)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_403(self):
        response = self.client.get(self.instance_url(USER_JOAO['username']), **self.kwargs)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_200(self):
        response = self.client.get(self.instance_url(USER_VASCO['username']), **self.kwargs)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertIn('uuid', response.data)
        self.assertEqual(response.data['username'], USER_VASCO['username'])
        self.assertEqual(response.data['email'], USER_VASCO['email'])

    def test_destroy_401(self):
        response = self.client.delete(self.instance_url(USER_VASCO['username']), format=self.CONTENT_TYPE)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_403(self):
        response = self.client.delete(self.instance_url(USER_JOAO['username']), **self.kwargs)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_204(self):
        self.assertEqual(User.objects.count(), 2)

        response = self.client.delete(self.instance_url(USER_VASCO['username']), **self.kwargs)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(User.objects.count(), 1)