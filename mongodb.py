from pymongo import MongoClient
from bson import ObjectId, json_util
import json, os
from passlib.hash import pbkdf2_sha256
from dotenv import load_dotenv
from flask import render_template


#Classes -----------------------------------------------------------------------------------
class JSONEncoder(json.JSONEncoder):

  def default(self, o):
    if isinstance(o, ObjectId):
      return str(o)
    return json.JSONEncoder.default(self, o)


#-------------------------------------------------------------------------------------------

#To load the .env---------------------------------------------------------------------------
load_dotenv()

#Setting up the mongodb database -----------------------------------------------------------
my_secret = os.getenv('MONGODB_PWD')
connection_string = f"mongodb+srv://enzotresmediano:{my_secret}@cluster0.hrke9xw.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(connection_string)
discordAPI_db = client["discordAPI"]
collectionLOGS = discordAPI_db["logs"]
collectionUSERS = discordAPI_db["users"]
collectionLOGGEDIN = discordAPI_db["signedIn"]
#-------------------------------------------------------------------------------------------

#functions ---------------------------------------------------------------------------------


def read():
  try:
    logs = []
    for el in collectionLOGS.find():
      logs.append(el)
  #list() nao funciona com mongodb ent useu for loop
  except Exception as e:
    return f"{e}", 400
  #print(JSONEncoder().encode(tarefas))
  return json.loads(json_util.dumps(logs))


def createLOG(query):
  try:
    ("Entered to create log")
    displayName = query["displayName"]
    authorName = query["authorName"]
    content = query["msgContent"]
    date = query["createAt"]
    print("POST let through")
    #print(tarefas)
    query = {
      "displayName": displayName,
      "authorName": authorName,
      "msgContent": content,
      "createAt": date
    }
    inserted_id = collectionLOGS.insert_one(query).inserted_id
    #The .inserted_id lets us see the value of the new id created for the item
    print(f"Item inserted with id: {inserted_id}")
    return JSONEncoder().encode(query), 201

  except Exception as e:
    return {"message": str(e)}, 400


def deleteLOGS(displayName):
  print(f"User: {displayName} about to get deleted")
  x = collectionLOGS.delete_many({"displayName": displayName})
  print("deleted")
  return f"Deleted: {x.deleted_count} of history"


def readLOGS(displayName):
  print(f"User: {displayName} about to get read")
  x = collectionLOGS.find({"authorName": displayName})
  print("read")
  return x


#APP vai trabalhar com update so porque usuario vai fazer os create, read, e delete
#@app.route('/tarefas', methods=["PUT"])
def update(item):
  try:
    id = item["_id"]
    _id = ObjectId(id)
    collectionLOGS.update_one(
      {"_id": _id},
      {
        "$set": {
          "displayName": item["displayName"],
          "authorName": item["authorName"],
          "msgContent": item["msgContent"],
          "createAt": item["createAt"]
        }
      },
    )
    item = collectionLOGS.find_one({"_id": _id})
  except Exception as e:
    return {"message": str(e)}, 400

  return json.loads(json_util.dumps(item)), 201


def createUser(query):
  if collectionUSERS.find_one({"name": query["name"]}):
    return [{"error": "Username already taken"}, 400]
  insertedID = collectionUSERS.insert_one(query).inserted_id
  print(insertedID)
  return [{"empty": "empty"}, 200]


def loginUser(query):
  result = collectionUSERS.find_one({"name": query["name"]})
  print(f"Result: {result}")
  if result and pbkdf2_sha256.verify(query["password"], result["password"]):
    if collectionLOGGEDIN.find_one({"name": query["name"]}):
      return [{"error": "Already logged in"}, 400]
    else:
      collectionLOGGEDIN.insert_one({
        "name": query["name"],
        "user": query["user"]
      })
      return [{"result": "You are now logged in"}, 200]
  else:
    return [{"result": "No account with that user"}, 400]


def signOutUser(query):
  print("query:")
  print(query)
  result = collectionLOGGEDIN.find_one({"user": query["user"]})
  if result == None:
    return [{"result": "No account was logged in"}, 400]
  else:
    collectionLOGGEDIN.delete_one({"user": query["user"]})
    return [{"result": "Account succesfully logged out"}, 200]


def check(author):
  try:
    print("checking authorization")
    print(author)
    user = collectionLOGGEDIN.find_one({"user": author})
    print("here")
    print(user)
    if collectionLOGGEDIN.find_one({"user": author}):
      print("True")
      return True
    else:
      print("False")
      return False
  except Exception as e:
    print(e)


# def registerUser(form):
#   try:
#     username = form["username"]
#     password = pbkdf2_sha256.hash(form["password"])
#   except Exception as e:
#     return e
