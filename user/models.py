from flask import Flask, jsonify, session
from passlib.hash import pbkdf2_sha256
from mongodb import createUser, loginUser, signOutUser
import uuid

class User:
  def __init__(self, user):
    self.user = user

  
  def signin(self):
    print("entered signin")    
    result = loginUser(self.user)
    return jsonify(result[0])

  def signout(self):
    print("user attempting signout")
    result = signOutUser(self.user)
    return jsonify(result[0])
      
  def signup(self):
    print("entered signup")
    print(self.user)
    print(self.user["name"])
    user = {
      "_id": uuid.uuid4().hex,
      "name": self.user["name"],
      "password": self.user["password"]
    }
    user["password"] = pbkdf2_sha256.hash(user["password"])
    result = createUser(user)
    print(result[0])
    return jsonify(result[0])
    