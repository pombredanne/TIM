import os
from base64 import b64decode
from pprint import pprint

from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from tests.db.timdbtest import TEST_USER_1_NAME, TEST_USER_2_NAME, TEST_USER_3_NAME
from tests.server.timroutetest import TimRouteTest
from tests.timliveserver import TimLiveServer


class BrowserTest(TimLiveServer, TimRouteTest):
    login_dropdown_path = '//login-menu/div/button'
    screenshot_dir = '/service/screenshots'

    def setUp(self):
        TimLiveServer.setUp(self)
        options = webdriver.ChromeOptions()
        # native headless mode does not work yet
        # options.add_argument('headless')
        # options.add_argument('disable-gpu')
        # options.add_argument('window-size=1024x768')
        # options.add_argument('no-sandbox')
        self.drv = webdriver.Remote(command_executor=self.app.config['SELENIUM_REMOTE_URL'] + ':4444/wd/hub',
                                    desired_capabilities=options.to_capabilities())
        self.drv.implicitly_wait(10)
        self.wait = WebDriverWait(self.drv, 10)

    def login_browser_as(self, email: str, password: str, name: str):
        self.client.__exit__(None, None, None)
        self.goto('')
        elem = self.drv.find_element_by_xpath('//login-menu/button')
        elem.click()
        elem.find_element_by_xpath("//input[@type='email']").send_keys(email)
        elem.find_element_by_xpath("//input[@type='password']").send_keys(password)
        elem.find_element_by_xpath("//button[@type='submit']").click()
        self.wait.until(ec.text_to_be_present_in_element((By.XPATH, self.login_dropdown_path), name))
        self.client.__enter__()

    def login_browser_quick_test1(self):
        """Logs testuser 1 in quickly by directly adding the session cookie to the browser."""
        self.goto("/empty")
        self.drv.delete_all_cookies()
        self.drv.add_cookie(
            {'class': 'org.openqa.selenium.Cookie',
             'domain': 'tim',
             'expiry': 7544144177,
             'hCode': 1984987798,
             'httpOnly': True,
             'name': 'session',
             'path': '/',
             'secure': False,
             'value': '.eJwtjEEKwzAMBL8S9mwaDD351EfkboS7pQHLCYoDhdK_V4bcZpiVvsg7TaWxdaRuJwOklfdmSEBAEWV-2aausztV1urcefT44Ed0r7wV7wFGqbn5gffF-3QetCl6GZDXJ9L94ms1vgyP-P0BRcctlw.DBglMQ.vvva2NpZfDBi7dlJAJoKfg5uGQo'})

    def login_browser_test1(self):
        """Logs in as Test user 1."""
        self.login_browser_as('test1@example.com', 'test1pass', TEST_USER_1_NAME)

    def login_browser_test2(self):
        """Logs in as Test user 2."""
        self.login_browser_as('test2@example.com', 'test2pass', TEST_USER_2_NAME)

    def login_browser_test3(self):
        """Logs in as Test user 3."""
        self.login_browser_as('test3@example.com', 'test3pass', TEST_USER_3_NAME)

    def goto(self, url: str):
        """Navigates to a new URL using the browser.

        :param url: The URL to which to navigate. This must be relative.

        """
        self.drv.get("{}:{}{}".format(self.app.config['SELENIUM_BROWSER_URL'], self.app.config['LIVESERVER_PORT'], url))

    def print_console(self):
        logs = self.drv.get_log("browser")
        pprint(logs)

    def save_screenshot(self, filename: str):
        """Saves the current browser screen to a PNG file in screenshots directory.

        :param filename: The file name of the PNG file.

        """

        os.makedirs(self.screenshot_dir, exist_ok=True)
        if not self.drv.save_screenshot(f'{self.screenshot_dir}/{filename}.png'):
            raise Exception('Screenshot failed')

    def save_element_screenshot(self, element: WebElement, filename: str, move_to_element: bool=False):
        """Saves the screenshot of an element to a PNG file.

        :param element: The element to save.
        :param filename: Filename for the image without extension.
        :param move_to_element: Whether to move to the element before taking screenshot. Use this if there is a
        possibility that the element is not in viewport.
        """
        os.makedirs(self.screenshot_dir, exist_ok=True)
        if move_to_element:
            ActionChains(self.drv).move_to_element(element).perform()
        src_base64 = self.drv.get_screenshot_as_base64()
        im = Image.open(BytesIO(b64decode(src_base64)))

        x = element.location["x"]
        y = element.location["y"]
        w = element.size["width"]
        h = element.size["height"]

        im = im.crop((x, y, x + w, y + h))
        im.save(f'{self.screenshot_dir}/{filename}.png')

    def should_not_exist(self, css_selector: str):
        """Asserts that the current document should not contain any elements that match the specified CSS selector.

        :param css_selector: The CSS selector to test.

        """
        self.drv.implicitly_wait(0.5)
        try:
            self.drv.find_element_by_css_selector(css_selector)
        except NoSuchElementException:
            pass
        else:
            self.assertTrue(False, 'Selector "{}" matched something.'.format(css_selector))
        finally:
            self.drv.implicitly_wait(10)

    def tearDown(self):
        TimLiveServer.tearDown(self)
        self.drv.quit()
