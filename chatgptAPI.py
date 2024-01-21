import openai, os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("CHATGPT_KEY")
openai.api_key = key
messages = [
  {
    "role": "system",
    "content": "You are a kind helpful assistant"
  },
]


def call(message):
  print(message)
  print("in message")
  try:
    if message:
      messages.append({"role": "user", "content": message}, )
      chat = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                          messages=messages)

    reply = chat.choices[0].message.content
    print(reply)
    messages.append({"role": "assistant", "content": reply})
    return reply
  except Exception as e:
    return(e)