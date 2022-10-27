import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import LiveServerTestCase, override_settings
from django.urls import reverse
from playwright.sync_api import sync_playwright

from .models import Article, Settings

small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)


@override_settings(DEBUG=True)
class IntegrationTests(LiveServerTestCase):
    playwright = None
    browser = None

    @classmethod
    def setUpClass(cls):
        os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.webkit.launch(headless=False)

        # Create article with wide table
        image = SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')

        Article.objects.create(
            title='Test Article',
            content='''<table id="test-table" style="overflow: scroll">
                <tr>
                    <td>Test</td>
                </tr>
            </table>''',
            slug='test-article',
            card_img=image,
            published_bool=True
        )

        page_settings = Settings.load()
        page_settings.logo = image
        page_settings.save()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def test_table_width(self):
        iphone = self.playwright.devices['iPhone 11 Pro']
        mobile_context = self.browser.new_context(**iphone)
        page = mobile_context.new_page()
        page.goto(f'{self.live_server_url}{reverse("article", args=["test-article"])}')
        screenshot = page.screenshot(path='screenshot.png')

        # Check if entire table is visible
        table = page.query_selector('#test-table')
        bbox = table.bounding_box()

        self.assertGreater(bbox['x'], 0)

        # Attempt to scroll table
        page.evaluate('''() => {
            let el = document.querySelector('#test-table');
            while (el.clientWidth >= el.scrollWidth) {
                el = el.parentElement;
            }
            el.scrollLeft = el.scrollWidth;
        }''')

        # Check if table is still visible
        bbox = table.bounding_box()
        self.assertLess(bbox['x'] + bbox['width'], page.viewport_size['width'])

        # save screenshot
        with open('screenshot.png', 'wb') as f:
            f.write(screenshot)
