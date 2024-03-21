import atexit
import csv
import os
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import requests, time
import logging
from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def warn(*args, **kwargs):
    pass


import warnings

warnings.warn = warn


class VeaBot:
    def __init__(self):
        self.current_url = ""
        self.all_products = []
        self.is_region_selected = False
        atexit.register(self.on_graceful_exit)
        self.available_regions = "https://www.vea.com.ar/api/dataentities/NT/search?_fields=name,grouping,image_maps,geocoordinates,SellerName,id,country,city,neighborhood,number,postalCode,state,street,PurchaseMessage&_where=isActive%3Dtrue+AND+hasPickup%3Dtrue&_sort=name+ASC&an=veaargentina"
        self.getAvailableRegions()
        print("You Selected {} shop in {} region".format(self.shop, self.region))
        LOGGER.setLevel(logging.ERROR)
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--log-level=OFF')
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
        self.driver.maximize_window()
        self.blockingUnwantedRequest()

        self.loop_targets()

    def loop_targets(self):
        with open('targets.txt', 'r') as f:
            links = [line.strip() for line in f]
        f.close()
        links = list(filter(None, links))
        for link in links:
            if "https://www.vea.com.ar/" in link:

                self.current_url = link
            else:
                self.current_url = "https://www.vea.com.ar/" + link
            print("We starting with {}".format(self.current_url))
            self.selectRegion()
        self.driver.close()

    def selectRegion(self):
        self.driver.get(self.current_url)
        if not self.is_region_selected:
            self.driver.find_element_by_css_selector(".b.vtex-rich-text-0-x-strong").click()
            time.sleep(2)
            self.driver.find_element_by_xpath("//h4[text()='Retiro en tienda']").click()
            time.sleep(2)
            self.driver.find_element_by_xpath(
                "//select[@name='provincia']/option[text()='{}']".format(self.region)).click()
            time.sleep(0.5)
            self.driver.find_element_by_xpath("//select[@name='tienda']/option[text()='{}']".format(self.shop)).click()
            self.is_region_selected = True
            self.StartShopping()
            self.StartedShopping()
        else:
            self.PhaseOne()

    def getAvailableRegions(self):
        r = requests.get(self.available_regions, headers={'REST-Range': 'resources=0-999', }).json()
        regions = []
        shops = []
        for region in r:
            regions.append(region['grouping'])
        regions = set(regions)
        print("Please Select a Region, Available Regions are: ", regions)
        self.region = input("Region: ")

        for shop in r:
            if shop['grouping'] == self.region:
                shops.append(shop['name'])
        print("Please Select a Shop, Available Shops for {}: ".format(self.region), shops)

        self.shop = input("Shop: ")

    def PhaseOne(self):
        self.FindAllProducts()
        self.FindProduct()
        self.SingleProductInfo()
        self.SaveFileToDisk()

    def FindAllProducts(self):
        while True:
            try:
                more_button = self.driver.find_element_by_xpath(
                    "//div[contains(@class,'vtex-search-result-3-x-buttonShowMore')]/div/button")
                # more_button = self.driver.find_element_by_xpath("//div[text()='Mostrar más']")
                actions = ActionChains(self.driver)
                actions.move_to_element(more_button).perform()
                background = self.driver.find_element_by_css_selector("body")
                background.send_keys(Keys.PAGE_DOWN)
                more_button.click()
                background.send_keys(Keys.PAGE_UP)
            except Exception as e:
                if self.CheckIfAllProducts():
                    break

    def CheckIfAllProducts(self):
        try:
            isAll = self.driver.find_element_by_css_selector(".progress")
            if isAll.get_attribute('style') == "width: 100%;":
                detectedProducts = self.driver.find_element_by_css_selector("#gallery-layout-container")
                count = detectedProducts.find_elements_by_css_selector(".vtex-search-result-3-x-galleryItem")
                print("We Fetched All #{}".format(len(count)))
                return True
            else:
                print("Loading ...")
                time.sleep(0.5)
                return False
        except Exception as e:
            return False

    def FindProduct(self):
        products = self.driver.find_elements_by_css_selector(".vtex-search-result-3-x-galleryItem")
        for i, product in enumerate(products):
            try:
                print("Product {} of {} in Phase 1".format(i + 1, len(products)))
                brand = product.find_element_by_css_selector(".vtex-product-summary-2-x-productBrandName").text
                summary = product.find_element_by_css_selector(
                    ".vtex-product-summary-2-x-productBrand.vtex-product-summary-2-x-brandName.t-body").text
                price = product.find_element_by_css_selector(".contenedor-precio").find_element_by_tag_name("span").text
                link = product.find_element_by_css_selector(".vtex-product-summary-2-x-clearLink").get_attribute("href")
                product_data = {
                    "brand": brand,
                    "summary": summary, "link": link, "price": price, "images": "", "id": "", "description": "",
                    "specs": ""
                }
                self.all_products.append(product_data)
            except Exception as e:
                print("Product {} has issue..".format(i + 1), e)
                continue
        print("We Got All Products. Now Fetching Each One")

    def SingleProductInfo(self):
        print("Starting PhaseTwo")
        for (i, product) in enumerate(self.all_products):
            self.driver.get(product['link'])
            self.WaitForProductInfo()
            self.FetchReset(product)
            print("Fetched {} of {}".format(i + 1, len(self.all_products)))

    def WaitForProductInfo(self):
        while True:
            try:
                self.driver.find_element_by_xpath("//div[contains(@class,'contenedor-precio')]/span").text
                break
            except Exception as e:
                time.sleep(0.5)
                print("Waiting for Product Info")
                if not self.IsProductAvailable():
                    break

    def IsProductAvailable(self):
        try:
            self.driver.find_element_by_css_selector('.vtex-store-components-3-x-productBrand')
            return True
        except Exception as e:
            return False

    def FetchReset(self, product):
        try:
            images = self.driver.find_elements_by_css_selector(".vtex-store-components-3-x-productImageTag")
            product_images = []
            for image in images:
                product_images.append(image.get_attribute("src"))
            product['images'] = ','.join([str(elem) for elem in product_images])
            product['id'] = self.driver.find_element_by_css_selector(
                ".vtex-product-identifier-0-x-product-identifier__value").text
            product['specs'] = self.GetTableData()
            product['description'] = self.GetDescription()
        except Exception as e:
            print("Something is Missing in the Data. Don't Worry we won't stuck on it. ")

    def GetTableData(self):
        specs = []
        t_specs = ""
        try:
            table_element = self.driver.find_elements_by_css_selector(
                ".vtex-product-specifications-1-x-specificationValue")
            for i, e in enumerate(table_element):
                name = self.driver.find_elements_by_css_selector(".vtex-product-specifications-1-x-specificationName")[
                    i].text
                specs_object = {"name": name, "value": e.text}
                specs.append(specs_object)
            t_specs = ','.join([str(elem) for elem in specs])
            return t_specs
        except Exception as e:
            print("Some Table Data are missing")

    def GetDescription(self):
        description = ""
        try:
            description = self.driver.find_element_by_xpath(
                "//div[contains(@class,'vtex-store-components-3-x-content')]/div/article/p").text
            return description
        except Exception as e:
            return description

    def blockingUnwantedRequest(self):
        self.driver.execute_cdp_cmd('Network.setBlockedURLs',
                                    {"urls": ["www.google-analytics.com", "https://onesignal.com/"]})
        self.driver.execute_cdp_cmd('Network.enable', {})

    def StartShopping(self):
        while True:
            try:
                shop_button = self.driver.find_element_by_xpath("//button[text()='Empezar a comprar']")
                print("shop button available now!")
                shop_button.click()
                break
            except Exception as e:
                print("Waiting For Start shopping...")
                time.sleep(0.5)

    def StartedShopping(self):
        while True:
            try:
                self.driver.find_element_by_xpath("/html/body/div[9]")
                print("We Waiting for Reload Page")
                time.sleep(0.5)
            except:
                print("Done. We are ready to start")
                self.PhaseOne()
                break

    def SaveFileToDisk(self):
        file_name = self.current_url.split("/")[-1]
        with open('{}_{}_{}_{}.csv'.format(self.region, self.shop, file_name, time.time()), 'w', newline='',
                  encoding="utf-8-sig", ) as Saver:
            headerList = ['Brand', 'Summary', 'Link', 'Price', 'Images', 'ID', "Description", "Specs"]
            dw = csv.DictWriter(Saver, delimiter=',', fieldnames=headerList)
            dw.writeheader()
            results_writer = csv.writer(Saver)
            for p in self.all_products:
                try:
                    results_writer.writerow(
                        [p['brand'], p['summary'], p['link'], p['price'], p['images'], p['id'], p['description'],
                         p['specs']])
                except Exception as e:
                    print("ERROR: Saving file error, ", e)
                    continue
            self.all_products = []
        Saver.close()

    def on_graceful_exit(self):
        # Check if already saved?
        file_name = self.current_url.split("/")[-1]
        isExisted = os.path.exists('{}_{}_{}.csv'.format(self.region, self.shop, file_name))
        if isExisted:
            print("File Saved Successfully")
        else:
            if len(self.all_products) > 0:
                self.SaveFileToDisk()
                print("File Saved Successfully")
            else:
                print("Nothing to be saved")


if __name__ == '__main__':
    app = VeaBot()
