from flask import Flask, request, render_template
from mongodb import update, read, createLOG, deleteLOGS, readLOGS, check
import os, asyncio, json, discord
import requests as req
from chatgptAPI import call
from webscrapper import getSongs
from threading import Thread
from user.models import User
from seleniumMine import checkRobloxNotification
from dotenv import load_dotenv
from pymongo import MongoClient

#To load the .env---------------------------------------------------------------------------
load_dotenv()

#Go to QAuth2 -> URL Generator, then click bot
DiscordToken = os.getenv("DISCORDBOT_KEY")
print(DiscordToken)
Flask_key = os.getenv("FLASK_KEY")
print(Flask_key)
intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(
  intents=intents)  #The intents on the right is the variable we made


class async_discord_thread(Thread):

  def __init__(self):
    Thread.__init__(self)
    self.loop = asyncio.get_event_loop()
    self.start()

  async def starter(self):
    await client.start(DiscordToken)

  def run(self):
    self.name = 'Discord.py'
    self.loop.create_task(self.starter())
    self.loop.run_forever()


#Discord code----------------------------------------------------------------------------------


@client.event
async def on_ready():  #Look into async def #Needs to be called on_ready
  print(f"{client.user} ta rodando!")


@client.event
async def on_message(msg):
  if msg.author == client.user:  #So that the it doesn't enter infinite loop
    return

  #print(msg.content)
  user_msg = str(msg.content)

  req.body = {
    "displayName": str(msg.author.display_name),
    "authorName": str(msg.author),
    "msgContent": str(msg.content),
    "createAt": str(msg.created_at)
  }

  print(f"{req.body['authorName']} said {req.body['msgContent']}")

  try:
    createLOG(req.body)
  except Exception as e:
    return {"message": str(e)}, 400

  # if "oi" in user_msg.lower():
  #   await msg.author.send("qual foi!")
  #   dumped = json.dumps(req.body, indent=2)
  #   x = req.post(
  #     url=
  #     "http://127.0.0.1:1500/",
  #     json=dumped)
  #   print(x.text)
  #   return

  if user_msg[0] == '%':
    if user_msg[1:9] == "register":
      split = user_msg.split("-")
      name = split[1]
      password = split[2]
      userJson = {"name": str(name), "password": str(password)}
      x = req.post(url="http://127.0.0.1:1500/user/signup", json=userJson)
      print("registering")
      if "error" in x.json():
        await msg.author.send(x.json()["error"])
      else:
        await msg.author.send("Succesfully created User")

    if user_msg[1:6] == "login":
      print("agf")
      split = user_msg.split("-")
      name = split[1]
      password = split[2]
      print("argh")
      loginDic = {"name": name, "user": str(msg.author), "password": password}
      print("woah")
      x = req.post(url="http://127.0.0.1:1500/user/login", json=loginDic)
      print("attempting login")
      if "error" in x.json().keys():
        print("error")
        await msg.author.send(x.json()["error"])
      else:
        print("not error")
        await msg.author.send(x.json()["result"])

    elif user_msg[1:7] == "logout":
      x = req.post(url="http://127.0.0.1:1500/user/logout",
                   json={"user": str(msg.author)})
      await msg.author.send(x.json()["result"])

  else:
    if check(str(msg.author)) == True:
      #Delte scenarios and if user isn't deleteing than it is createing a log
      if user_msg[0] == '!':
        if "deleteM" in user_msg:
          deleteMessage = (deleteLOGS(msg.author.display_name))
          await msg.author.send(deleteMessage)
        elif "deleteP" in user_msg:
          if str(msg.author) == "em57530":
            split = str(msg.content).split(" ")
            deleteMessage = (deleteLOGS(split[1]))
            await msg.author.send(deleteMessage)
          else:
            await msg.author.send("Must be admin to use this command!")

      #Read scenarios
      if user_msg[0] == '!' and "read" in user_msg:
        if str(msg.author) == "em57530":
          split = str(msg.content).split(" ")
          toRead = split[1]
          readItems = (readLOGS(toRead))
          await msg.author.send(f"Items by {toRead}")
          for el in readItems:
            await msg.author.send(f"Item: {el['msgContent']}")

      #The ? will be used as a command to acces bs4, selenium, chatgpt, etc
      if user_msg[0] == '?':
        if "songs" in user_msg:
          print("getting songs")
          split = user_msg.split("-")
          songs = getSongs(int(split[1]), int(split[2]))
          for song in songs:
            await msg.author.send(
              f"{song['num']}) {song['name']} by {song['author']}")

        elif "roblox" in user_msg:
          print("getting roblox")
          split = user_msg.split("-")
          print(split)
          user = split[1]
          password = split[2]
          notif = checkRobloxNotification(user, password)

          await msg.author.send(
            f"You have {notif} notifications waiting in Roblox")

        else:
          print("User talking to chatgpt")
          await msg.author.send(call(user_msg[1:]))
        return


#Flask code----------------------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = Flask_key


@app.route('/', methods=["POST"])
def index():
  print("entered")
  if request.method == "POST":
    print("Is method POST")
    item = request.json
  print("rendering")
  return item


@app.route('/user/login', methods=["POST"])
def login():
  print('Login')
  item = request.json
  user = User(item)
  print(user)
  return user.signin()


@app.route("/user/signup", methods=["POST"])
def signup():
  item = request.json
  user = User(item)
  return user.signup()


@app.route("/user/register", methods=["GET", "POST"])
def register():
  if request.method == 'POST':
    form = request.form
    user = User(form)
    print(f"User: {user}")
    return user.signup()
  return render_template("index.html")


@app.route('/user/logout', methods=["POST"])
def logout():
  item = request.json
  user = User(item)
  return user.signout()


@app.route('/LOGS', methods=["GET"])
def readMongoDBLOG():
  print("attempting to read LOGS")
  readitem = read()
  return readitem


@app.route('/foo')
def foo():
  return request.base_url


@app.route('/updateLOG',
           methods=["PUT"])  #Create, read, and delete in mongodb.py
def updateMongoDBLOG():
  item = request.json
  update(item)


if __name__ == '__main__':

  discord_thread = async_discord_thread()
  app.run(host="0.0.0.0", port=1500)
