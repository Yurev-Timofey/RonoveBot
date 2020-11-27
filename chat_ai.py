# import dialogflow
# import json
#
# api_ai_token = open('api_ai_token.txt').read()
#
# request = apiai.ApiAI(api_ai_token).text_request()  # Токен API к Dialogflow
# request.lang = 'ru'  # На каком языке будет послан запрос
# request.session_id = 'myAIBot'  # ID Сессии диалога (нужно, чтобы потом учить бота)
# request.query = input()  # Посылаем запрос к ИИ с сообщением от юзера
#
# responseJson = json.loads(request.getresponse().read().decode('utf-8'))
# # response = responseJson['result']['fulfillment']['messages'][0]['speech']  # Разбираем JSON и вытаскиваем ответ
# # Если есть ответ от бота - присылаем юзеру, если нет - бот его не понял
# print(responseJson)
# def explicit():
#     from google.cloud import storage
#
#     # Explicitly use service account credentials by specifying the private key
#     # file.
#     storage_client = storage.Client.from_service_account_json(
#         'service_account.json')
#
#     # Make an authenticated API request
#     # buckets = list(storage_client.list_buckets())
#     # print(buckets)
#     print(storage_client.project)
#
#
# explicit()

# session_client = dialogflow.SessionsClient
# # session = session_client.from_service_account_json('service_account.json')
# session = session_client.from_service_account_json('service_account.json')
#
# text_input = dialogflow.types.TextInput(text="Привет", language_code="ru")
# query_input = dialogflow.types.QueryInput(text=text_input)
# response = session_client.detect_intent(session=session_c, query_input=query_input)
import os
from time import sleep

import dialogflow
from google.api_core.exceptions import InvalidArgument

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'service_account.json'

DIALOGFLOW_PROJECT_ID = 'small-talk-utfv'
DIALOGFLOW_LANGUAGE_CODE = 'ru'
SESSION_ID = 'me'

session_client = dialogflow.SessionsClient()
session = session_client.session_path(DIALOGFLOW_PROJECT_ID, SESSION_ID)

i = 0


def check_message():
    path = "from_discord.fifo"
    if not os.path.exists(path):
        return

    message = open(path).read()

    if message != '':
        send_message(message)


def send_message(message):
    global i

    text_input = dialogflow.types.TextInput(text=message, language_code=DIALOGFLOW_LANGUAGE_CODE)
    query_input = dialogflow.types.QueryInput(text=text_input)
    try:
        response = session_client.detect_intent(session=session, query_input=query_input)
    except InvalidArgument:
        raise

    path = "to_discord.fifo"
    if not os.path.exists(path):
        os.mkfifo(path)

    i += 1

    pipe = open(path, "w")
    pipe.write(str(i) + '$space$' + str(response.query_result.fulfillment_text))
    pipe.close()


while True:
    check_message()
    sleep(1)
