import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys


def checkRobloxNotification(user, passer):
  print("In function")
  options = webdriver.ChromeOptions()

  print("Chromedriver")

  try:
    options.add_experimental_option("detach", True)
    options.add_argument("--start-maximized")

    browser = webdriver.Chrome(options = options, service = Service("Tarefa 8 Ultimate Discord Bot/drivers/chromedriver.exe"))

  except Exception as e:
    print(e)

  print("In service")

  time.sleep(1)

  browser.get("https://www.roblox.com/Login")
  time.sleep(3)

  print("In browser")

  username = browser.find_element(by=By.NAME, value="username")
  time.sleep(1)
  password = browser.find_element(by=By.NAME, value="password")
  time.sleep(1)
  print("Got keys")

  print(user)
  print(password)

  username.send_keys(user)
  time.sleep(1)
  password.send_keys(passer)

  print("Sent keys")
  time.sleep(1)

  loginButton = browser.find_element(by=By.ID, value="login-button")
  loginButton.click()
  time.sleep(6)

  print("logged in")



  time.sleep(1)

  notif = browser.find_element(By.XPATH, value = '//*[@id="nav-friends"]/div[2]/span').text
  #notif = browser.find_element(By.CLASS_NAME, value = "notification-blue notification").text

  print(notif)





  return notif
