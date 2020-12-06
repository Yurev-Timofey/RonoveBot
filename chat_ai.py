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
