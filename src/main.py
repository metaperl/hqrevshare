#!/usr/bin/env python


from __future__ import print_function
# Core
import collections
from functools import wraps
import logging
import pprint
import random
import re
import time
import ConfigParser
from decimal import *

# Third-Party
import argh
from clint.textui import progress
import html2text
from PIL import Image
from splinter import Browser
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import \
    TimeoutException, UnexpectedAlertPresentException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.support.expected_conditions as EC
import selenium.webdriver.support.ui as ui

# Local

logging.basicConfig(
    format='%(lineno)s - %(message)s',
    level=logging.INFO
)

random.seed()

pp = pprint.PrettyPrinter(indent=4)

base_url = 'http://www.hqrevshare.com/'

action_path = dict(
    login='login.php',
    view_ads='member/surf.php',
    dashboard='Dot_MembersPage.asp',
    withdraw='DotwithdrawForm.asp',
    buy_pack='purchase.php',
    transfer_balance='transfer_rbalance.php'
    )

one_minute = 60
three_minutes = 3 * one_minute
ten_minutes = 10 * one_minute
one_hour = 3600


def url_for_action(action):
    return "{0}/{1}".format(base_url, action_path[action])


def loop_forever():
    while True:
        pass

def get_outer_html(driver, elem):
    return driver.execute_script("return arguments[0].outerHTML;", elem)

def clear_input_box(box):
    box.type(Keys.CONTROL + "e")
    for i in xrange(100):
        box.type(Keys.BACKSPACE)
    return box


# http://stackoverflow.com/questions/16807258/selenium-click-at-certain-position
def click_element_with_offset(driver, elem, x, y):
    action = ActionChains(driver)
    echo_print("Moving to x position", x)
    echo_print("Moving to y position", y)
    action.move_to_element_with_offset(elem, x, y)
    print("OK now see where the mouse is...")
    action.click()
    action.perform()


def page_source(browser):
    document_root = browser.driver.page_source
    return document_root


def wait_visible(driver, locator, by=By.XPATH, timeout=300):
    """

    :param driver:
    :param locator:
    :param by:
    :param timeout:
    :return:
    """
    try:
        if ui.WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, locator))):
            return driver.find_element(by, locator)
    except TimeoutException:
        return False


def maybe_accept_alert(driver):
    try:
        logging.warn("Probing for alert.")
        ui.WebDriverWait(driver, 3).until(EC.alert_is_present(),
                                          'Timed out waiting for PA creation ' +
                                          'confirmation popup to appear.')

        alert = driver.switch_to_alert()
        alert.accept()
        print("alert accepted")
    except TimeoutException:
        print("no alert")


def trap_unexpected_alert(func):
    @wraps(func)
    def wrapper(self):
        try:
            return func(self)
        except UnexpectedAlertPresentException:
            print("Caught unexpected alert.")
            return 254
        except WebDriverException:
            print("Caught webdriver exception.")
            return 254

    return wrapper


def trap_alert(func):
    @wraps(func)
    def wrapper(self):
        try:
            return func(self)
        except UnexpectedAlertPresentException:
            logging.info("Caught UnexpectedAlertPresentException.")
            alert = self.browser.driver.switch_to_alert()
            alert.accept()
            return 254
        except WebDriverException:
            print("Caught webdriver exception.")
            return 253

    return wrapper


def get_element_html(driver, elem):
    return driver.execute_script("return arguments[0].innerHTML;", elem)


def echo_print(text, elem):
    print("{0}={1}.".format(text, elem))


# https://stackoverflow.com/questions/10848900/how-to-take-partial-screenshot-frame-with-selenium-webdriver/26225137#26225137?newreg=8807b51813c4419abbb37ab2fe696b1a


def element_screenshot(driver, element, filename):
    t = type(element).__name__

    if t == 'WebDriverElement':
        element = element._element
    bounding_box = (
        element.location['x'],  # left
        element.location['y'],  # upper
        (element.location['x'] + element.size['width']),  # right
        (element.location['y'] + element.size['height'])  # bottom
    )
    bounding_box = map(int, bounding_box)
    echo_print('Bounding Box', bounding_box)
    return bounding_box_screenshot(driver, bounding_box, filename)


def bounding_box_screenshot(driver, bounding_box, filename):
    driver.save_screenshot(filename)
    base_image = Image.open(filename)
    cropped_image = base_image.crop(bounding_box)
    base_image = base_image.resize(
        [int(i) for i in cropped_image.size])
    base_image.paste(cropped_image, (0, 0))
    base_image.save(filename)
    return base_image


class Entry(object):
    def __init__(self, username, password, browser):
        self._username = username
        self._password = password
        self.browser = browser

    def login(self):
        print("Logging in...")

        self.browser_visit('login')

        for i in progress.bar(range(60)):
            sleep(random() * 0.2)

        for i in progress.dots(range(60)):
            sleep(random() * 0.2)

        self.browser.find_by_name('username').type(self._username)
        self.browser.find_by_name('password').type("{0}\t".format(self._password))

        button = self.browser.find_by_id('login')
        button.click()

        link_elem = wait_visible(self.browser.driver, "//a[@title='Close']", timeout=30)
        if link_elem:
            logging.info("close button ={0}".format(link_elem))
            link_elem.click()
        else:
            logging.info("No close button.")
            self.login()

    def browser_visit(self, action_label):
        try:
            print("Visiting URL for {0}".format(action_label))
            self.browser.visit(url_for_action(action_label))
            if action_label == 'view_ads':
                maybe_accept_alert(self.browser.driver)
            return 0
        except UnexpectedAlertPresentException:
            print("Caught UnexpectedAlertPresentException.")
            logging.warn("Attempting to dismiss alert")
            alert = self.browser.driver.switch_to_alert()
            alert.dismiss()
            return 254
        except WebDriverException:
            print("Caught webdriver exception.")
            return 253

    def view_ads(self, surf_amount):
        for i in xrange(1, surf_amount + 1):
            while True:
                print("Viewing ad {0}".format(i))
                result = self.view_ad()
                if result == 0:
                    break

    @trap_alert
    def view_ad(self):
        logging.warn("Visiting viewads")
        self.browser_visit('view_ads')

        time.sleep(random.randrange(2, 5))

        wait_visible(self.browser.driver, '//p')

        candidate_images_elem = self.browser.find_by_xpath('//div[@id="site_loader"]/img')
        image_count = collections.defaultdict(lambda: 0)
        for image in candidate_images_elem:
            image_count[image['src']] += 1
            if image_count[image['src']] > 1:
                image.click()
                return 0

        return 255

    def wait_on_ad(self):
        time_to_wait_on_ad = random.randrange(40, 50)
        for _ in progress.bar(range(time_to_wait_on_ad)):
            time.sleep(1)

    def transfer_balance(self):
        self.browser_visit('transfer_balance')

        account_balance_elem = self.browser.find_by_id("myTabContent").first
        account_balance_html = get_outer_html(self.browser.driver, account_balance_elem._element)
        account_balance_text = html2text.HTML2Text().handle(account_balance_html)
        floating_point_regexp = re.compile('\d+\.\d+')
        main, repurchase = [Decimal(f) for f in floating_point_regexp.findall(account_balance_text)][0:2]
        self._balance = dict(
            main=main, repurchase=repurchase
        )
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self._balance)
        self.browser.find_by_xpath("//input")[1].type(
            "{0}\n".format(main))


    def buy_pack(self):
        logging.info("Buy_pack...")
        self.transfer_balance()
        self.browser_visit('buy_pack')

        select = ui.Select(
            wait_visible(self.browser.driver, "paymentmethod", By.ID)
        )
        select.select_by_visible_text("Repurchase Balance")
        i = self.browser.find_by_name('withdrawAmt')
        self.browser.find_by_xpath('//input[@type="submit"]').click()

    def calc_account_balance(self):
        time.sleep(1)

        logging.warn("visiting dashboard")
        self.browser_visit('dashboard')

        logging.warn("finding element by xpath")
        elem = self.browser.find_by_xpath(
            '/html/body/table[2]/tbody/tr/td[2]/table/tbody/tr/td[2]/table[6]/tbody/tr/td/table/tbody/tr[2]/td/h2[2]/font/font'
        )

        print("Elem Text: {}".format(elem.text))

        self.account_balance = float(elem.text[1:])

        print("Available Account Balance: {}".format(self.account_balance))

    def calc_credit_packs(self):
        time.sleep(1)

        logging.warn("visiting dashboard")
        self.browser_visit('dashboard')

        logging.warn("finding element by xpath")
        elem = self.browser.find_by_xpath(
            "//font[@color='#009900']"
        )

        print("Active credit packs = {0}".format(elem[0].text))
        # for i, e in enumerate(elem):
        #     print("{0}, {1}".format(i, e.text))


def main(conf, surf=False, buy_pack=False, stay_up=False, surf_amount=12):
    config = ConfigParser.ConfigParser()
    config.read(conf)
    username = config.get('login', 'username')
    password = config.get('login', 'password')

    with Browser() as browser:
        browser.driver.set_window_size(1200, 1100)
        browser.driver.set_window_position(300, 0)
        browser.driver.set_page_load_timeout(160)

        e = Entry(username, password, browser)

        e.login()
        logging.info("LOgin complete.")

        if buy_pack:
            e.buy_pack()

        if surf:
            e.view_ads(surf_amount)

        if stay_up:
            loop_forever()


if __name__ == '__main__':
    argh.dispatch_command(main)
