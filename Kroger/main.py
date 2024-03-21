import atexit
import csv
import json

from bs4 import BeautifulSoup
import undetected_chromedriver as uc

import requests, time
import logging
from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.common.keys import Keys
import warnings
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


def warn(*args, **kwargs):
    pass


warnings.warn = warn


class Kronger:
    def __init__(self):
        self.current_url = ""
        self.search_url = "https://www.kroger.com/search?query={}"
        self.products = []
        self.location_cookie = ""
        LOGGER.setLevel(logging.ERROR)
        # chrome_options = webdriver.ChromeOptions()

        # chrome_options.add_argument('--log-level=OFF')

        self.ZipCode = input("Input ZIP Code: ")

        addresses = self.GetAvailableLocationsFromZipCode()
        print("Available Locations of {} Code: {}".format(self.ZipCode, addresses))
        print("Select the Store")
        self.LocationStore = input("Location Store: ")
        self.driver = uc.Chrome()
        self.driver.delete_all_cookies()
        self.driver.maximize_window()
        self.driver.get("https://www.kroger.com/")
        self.SelectLocation()
        self.LoopTargets()

    def LoopTargets(self):
        with open('targets.txt', 'r') as f:
            links = [line.strip() for line in f]
        f.close()
        links = list(filter(None, links))
        for link in links:
            if "https://www.kroger.com/pl/" in link:

                self.current_url = link
            else:
                self.current_url = self.search_url.format(link)
            print("We starting with {}".format(self.current_url))
            self.Service()

    def GetAvailableLocationsFromZipCode(self):
        try:
            addresses = []
            payload = json.dumps({
                "address": {
                    "postalCode": str(self.ZipCode)
                }
            })
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0',
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Origin': 'https://www.kroger.com',
                'Referer': 'https://www.kroger.com/',
            }
            stores = \
                requests.post("https://www.kroger.com/atlas/v1/modality/options", data=payload, headers=headers).json()[
                    'data'][
                    'modalityOptions']['storeDetails']

            for i, store in enumerate(stores):
                name = store['address']['address']['name']
                index = i + 1
                addresses.append({"name": name})
            if len(addresses) == 0:
                print("No Stores in this zip code.")
                exit()
            return addresses
        except Exception as error:
            print("ZipCode is not correctly formatted")
            exit()

    def SelectLocation(self):
        try:
            self.driver.find_element("xpath", "//span[contains(@class,'CurrentModality-modalityType')]").click()
            self.LoadingSpinnerChecker()
            postal_code_input = self.driver.find_element("xpath", "//input[contains(@autocomplete,'postal-code')]")
            postal_code_input.clear()
            postal_code_input.send_keys(self.ZipCode)
            time.sleep(2)
            self.driver.find_element("xpath", "//input[contains(@autocomplete,'postal-code')]").send_keys(Keys.ENTER)
            self.driver.find_element("xpath", "//button[contains(@class,'kds-SolitarySearch-button')]").click()
            self.LoadingSpinnerChecker()
            self.TryClickOnStore()
            self.LoadingSpinnerChecker()
            time.sleep(1)
            self.ClickOnLocation()
            self.ShimmerEffectChecker()
            print("Location selected successfully")
        except Exception as e:
            print(e)

            exit()

    def ClickOnLocation(self):
        select_store_path = "//button[contains(@aria-label,'{}')]".format(
            self.LocationStore)
        while True:
            try:
                self.driver.find_element("xpath", select_store_path).click()
                break
            except:
                print("waiting loading location or not available")
                time.sleep(0.5)

    def TryClickOnStore(self):
        while True:
            try:
                self.driver.find_element("xpath",
                                         "//button[contains(@data-testid,'ModalityOption-Button-IN_STORE')]").click()
                break
            except:
                print("Waiting for click on IN_STORE")
                time.sleep(2)

    def DeleteSession(self):
        self.driver.delete_cookie("ak_bmsc")

    def CheckingIsFailureLoad(self):
        self.LoadingSpinnerChecker()
        try:
            self.driver.find_element("xpath", "//h2[contains(@class,'kds-Heading kds-Heading--l mx-auto mb-16')]")
            self.DeleteSession()
            refresh_button = self.driver.find_element("xpath",
                                                      "//button[contains(@class,'kds-Button kds-Button--primary px-24')]")
            refresh_button.click()

            while True:
                try:
                    refresh_button = self.driver.find_element("xpath",
                                                              "//button[contains(@class,'kds-Button kds-Button--primary px-24')]")
                    refresh_button.click()
                    self.LoadingSpinnerChecker()
                except:
                    break

            time.sleep(2)
        except:
            print("Finally Loaded")

    def RemovePopup(self):
        print("Checking if there's popup")
        try:
            self.driver.find_element("xpath", "//button[contains(@aria-label,'Close pop-up')]").click()
            print("Popup Closed")
        except Exception:
            print("No Popups")

    def Service(self):
        self.driver.get(self.current_url)
        self.RemovePopup()
        time.sleep(1)
        self.GetHomeInfo()

    def GetHomeInfo(self):
        self.LoadingSpinnerChecker()
        self.CheckingIsFailureLoad()
        total = self.driver.find_elements("xpath", "//a[contains(@class,'kds-Pagination-link')]")[-1].get_attribute(
            'innerHTML')
        total = int(total)
        if total == 1:
            self.LoadingSpinnerChecker()
            self.GetHomeProducts(1)
            self.DeleteSession()
            print("We got all products in home pages")
            self.GetSingleProduct()
        else:
            current = 1
            while current != total:
                if "pl" in self.current_url:
                    page = "?page={}"
                else:
                    page = "&page={}"
                self.driver.get(self.current_url + page.format(current))
                self.LoadingSpinnerChecker()
                self.GetHomeProducts(current)
                self.DeleteSession()

                current += 1
            else:
                print("We got all products in home pages")
                self.GetSingleProduct()

    def GetSingleProduct(self):
        for i, product in enumerate(self.products):
            try:
                self.DeleteSession()
                self.ProductFetcher(product, i)
            except:
                self.DeleteSession()
                self.driver.refresh()
                self.ProductFetcher(product, i)
        print("We got all products <3")
        self.driver.quit()
        self.SaveFileToDisk()

    def ProductFetcher(self, product, i):
        try:
            self.driver.get(product['link'])
            self.LoadingSpinnerChecker()
            units = self.GetProductUnits()
            p_id = self.GetProductID()
            description = self.GetProductDescription()
            product['id'] = p_id
            product['quantity'] = units
            product['description'] = description
            product['delivery_price'] = self.GetCurrentPriceFormProduct()
            product['delivery_original'] = self.GetOriginalPriceFormProduct()
            product['image'] = self.GetAllImages()
            print("We got product #{} of #{}".format(i + 1, len(self.products)))
        except:
            print("Some Properties are not available")

    def GetAllImages(self):
        try:
            all_images = []
            images = self.driver.find_elements(
                "//button[contains(@class,'kds-SelectionCarousel-itemButton')]/div/div/img")
            for image in images:
                all_images.append(image.get_attribute("src"))
            return ','.join(str(e) for e in all_images)
        except:
            return ''

    def GetProductID(self):
        while True:
            try:
                return self.driver.find_element("xpath", "//span[contains(@class,'ProductDetails-upc')]").text
                break
            except:
                print("Waiting for ID")
                time.sleep(0.5)

    def GetProductDescription(self):
        try:
            description_html = self.driver.find_element("xpath",
                                                        "//div[contains(@class,'RomanceDescription')]").get_attribute(
                "innerHTML")
            text = BeautifulSoup(description_html, features="html.parser").get_text()
            return str(text)
        except Exception:
            return "No Description Detected!"

    def GetProductUnits(self):
        try:
            return self.driver.find_element("xpath", "//span[contains(@id,'ProductDetails-sellBy-unit')]").text
        except:
            try:
                return self.driver.find_element("xpath",
                                                '//*[@id="content"]/div/div/div[1]/div[2]/div[2]/div[2]/div[1]/div/label/span[2]').text
            except:
                return "No Units"

    def GetHomeProducts(self, page):
        self.CheckingIsFailureLoad()
        products = self.driver.find_elements("xpath", "//div[contains(@class,'kds-Card ProductCard')]")
        print("Products in Page #{} are: {}".format(page, len(products)))
        for i, product in enumerate(products):
            price = self.GetExactPrice(i)
            original_price = self.GetOriginalPrice()
            title = self.driver.find_elements("xpath", "//h3[contains(@data-qa,'cart-page-item-description')]")[i].text
            product_link = self.driver.find_elements("xpath",
                                                     "//a[contains(@class,'ProductDescription-truncated')]")[
                i].get_attribute(
                "href")
            image = self.driver.find_elements("xpath", "//img[contains(@data-qa,'cart-page-item-image-loaded')]")[
                i].get_attribute("src")
            product_object = {
                "title": title,
                "category_price": price,
                "original_price": original_price,
                "link": product_link,
                "image": image,
                "quantity": "",
                "id": "",
                "description": "",
                "delivery_original": "",
                "delivery_price": ""
            }
            self.products.append(product_object)
            print("We got product #{} of #{} in Page #{}".format(i + 1, len(products), page))

    def GetOriginalPrice(self):
        try:
            original_price = self.driver.find_element("xpath", "//s[contains(@class,'kds-Price-original')]").text
            return original_price
        except:
            return "No Original Price"

    def GetExactPrice(self, i):
        try:
            return self.driver.find_elements("xpath", "//div[contains(@class,'ProductCard')]/div/data")[
                i].get_attribute(
                "value")
        except:
            self.driver.find_element("xpath", "//span[contains(@class,'kds-Text--m block')]")
            return "Price May Vary"

    def GetCurrentPriceFormProduct(self):
        try:
            html_price = self.driver.find_element("xpath",
                                                  "//label[contains(@for,'DELIVERY')]/div/div/div/div/data/mark").get_attribute(
                "innerHTML")
            price = BeautifulSoup(html_price, features="html.parser").get_text()
            return price
        except:
            return "No Current Price"

    def GetOriginalPriceFormProduct(self):
        try:
            return self.driver.find_element("xpath",
                                            "//label[contains(@for,'DELIVERY')]/div/div/div/div/data/s").get_attribute(
                "innerHTML")
        except:
            return "No Original Price"

    def LoadingSpinnerChecker(self):
        path = "//label[contains(@class,'kds-LoadingSpinner')]"
        while True:
            try:
                self.driver.find_element("xpath", path)
                print("Waiting Loading..")
                time.sleep(0.5)
            except Exception:
                print("Loaded")
                break

    def ShimmerEffectChecker(self):
        path = "//div[contains(@class,'CurrentModalityTombstone-animated-background')]"
        while True:
            try:
                self.driver.find_element("xpath", path)
                print("Waiting Loading..")
                time.sleep(0.5)
            except Exception:
                print("Loaded")
                break

    def SaveFileToDisk(self):
        with open('{}_{}_{}.csv'.format(self.ZipCode, self.LocationStore, time.time()), 'w', newline='',
                  encoding="utf-8-sig", ) as Saver:
            headers = ['Title', 'Category Price', 'Delivery Current Price', 'Delivery Original Price', 'Link', 'Image',
                       'Quantity', "ID", "Description"]
            dw = csv.DictWriter(Saver, delimiter=',', fieldnames=headers)
            dw.writeheader()
            results_writer = csv.writer(Saver)
            for p in self.products:
                try:

                    results_writer.writerow(
                        [p['title'], p['category_price'], p['delivery_price'], p['delivery_original'], p['link'],
                         p['image'], p['quantity'],
                         p['id'],
                         p['description']])
                except Exception as e:
                    print("ERROR: Saving file error, ", e)
                    continue
            self.products = []
        Saver.close()


if __name__ == '__main__':
    app = Kronger()
