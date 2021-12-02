from django.test import TestCase
from .utils import extract_username_from_url

# Create your tests here.
class GitHubTestCase(TestCase):
    username = "zhpeng811"

    def test_regex_short(self):
        extracted_username = extract_username_from_url(f"github.com/{self.username}")
        self.assertEqual(self.username, extracted_username)
    
    def test_regex_short_with_trailing_slash(self):
        extracted_username = extract_username_from_url(f"github.com/{self.username}/")
        self.assertEqual(self.username, extracted_username)
    
    def test_regex_with_www(self):
        extracted_username = extract_username_from_url(f"www.github.com/{self.username}")
        self.assertEqual(self.username, extracted_username)

    def test_regex_with_protocol(self):
        extracted_username = extract_username_from_url(f"https://github.com/{self.username}/")
        self.assertEqual(self.username, extracted_username)

    def test_regex_with_full_path(self):
        extracted_username = extract_username_from_url(f"https://www.github.com/{self.username}/")
        self.assertEqual(self.username, extracted_username)