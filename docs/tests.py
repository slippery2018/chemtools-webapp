import os

from django.test import Client, TestCase
from django.core.urlresolvers import reverse
from django.core.management import call_command

import views


class DocsTestCase(TestCase):

    def setUp(self):
        self.client = Client()

    def test_index(self):
        response = self.client.get(reverse(views.index))
        self.assertEqual(response.status_code, 200)

    def test_doc_pages(self):
        names = os.listdir("docs/other")
        pages = [x.replace("_plain", "").replace(".md", "") for x in names]
        pages += ["technical"]

        for page in pages:
            response = self.client.get(reverse(views.docs_pages, args=(page, )))
            self.assertEqual(response.status_code, 200)

    def test_doc_pages_404(self):
        response = self.client.get(reverse(views.docs_pages, args=("notarealpage", )))
        self.assertEqual(response.status_code, 404)

    def test_make_docs(self):
        call_command("make_docs")