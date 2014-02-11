import os

from django.conf import settings
from django.test import Client, TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils import simplejson

import views
from project.utils import get_sftp_connection, get_ssh_connection, AESCipher


class SSHPageTestCases(TestCase):
    def setUp(self):
        user = User.objects.create_user("testerman", email="test@test.com", password="S0m3thing")
        user.save()
        self.client = Client()

    def test_job_index(self):
        response = self.client.get(reverse(views.job_index))
        self.assertEqual(response.status_code, 302)

        r = self.client.login(username="testerman", password="S0m3thing")
        self.assertTrue(r)
        response = self.client.get(reverse(views.job_index))
        self.assertEqual(response.status_code, 200)

    def test_get_job_list(self):
        response = self.client.get(reverse(views.get_job_list))
        self.assertEqual(response.status_code, 302)

    def test_get_job_list_auth(self):
        user = User.objects.get(username="testerman")
        r = self.client.login(username="testerman", password="S0m3thing")
        self.assertTrue(r)

        response = self.client.get(reverse(views.get_job_list))
        self.assertEqual(response.status_code, 200)
        data = simplejson.loads(response.content)
        self.assertTrue(data["is_authenticated"])


class UtilsTestCase(TestCase):
    def test_get_sftp_password(self):
        sftp = get_sftp_connection("localhost", "vagrant", password="vagrant", port=2222)
        with sftp:
            pass

    def test_get_sftp_key(self):
        with open(os.path.join(settings.MEDIA_ROOT, "tests", "id_rsa"), 'r') as key:
            sftp = get_sftp_connection("localhost", "vagrant", key=key, port=2222)
            with sftp:
                pass

    def test_get_sftp_error(self):
        with self.assertRaises(Exception):
            get_sftp_connection("localhost", "username")

    def test_get_ssh_password(self):
        ssh = get_ssh_connection("localhost", "vagrant", password="vagrant", port=2222)
        with ssh:
            pass

    def test_get_ssh_key(self):
        with open(os.path.join(settings.MEDIA_ROOT, "tests", "id_rsa"), 'r') as key:
            ssh = get_ssh_connection("localhost", "vagrant", key=key, port=2222)
            with ssh:
                pass

    def test_get_ssh_error(self):
        with self.assertRaises(Exception):
            get_ssh_connection("localhost", "username")

    def test_AES(self):
        cipher = AESCipher()
        string = "The quick brown fox jumps over the lazy dog."
        ct = cipher.encrypt(string)
        pt = cipher.decrypt(ct)
        self.assertEqual(pt, string)

    def test_AES_error(self):
        cipher = AESCipher()
        string = "The quick brown fox jumps over the lazy dog."
        ct = cipher.encrypt(string)[:10] + "randomgarbage"
        self.assertRaises(TypeError, cipher.decrypt, ct)
