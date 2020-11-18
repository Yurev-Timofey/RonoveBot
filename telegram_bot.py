import os
import telebot
from telebot import types

token = open('telegram_token.txt', 'r').read()
bot = telebot.TeleBot(token)
print('Logged in telegram as @{}'.format(bot.get_me().username))

global discord_channel_id


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Привет!")
    choose_discord_channel(message)


def choose_discord_channel(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    item1 = types.InlineKeyboardButton("флудилка-мусорка", callback_data='1')
    item2 = types.InlineKeyboardButton("элитная-флудилка", callback_data='2')
    item3 = types.InlineKeyboardButton("курилка", callback_data='3')
    markup.add(item1, item2, item3)
    bot.send_message(message.chat.id, text='Выбери канал в который хочешь отправить сообщение', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global discord_channel_id
    try:
        if call.message:
            if call.data == '1':
                discord_channel_name = "флудилка-мусорка"
                discord_channel_id = 683628281752191012
            elif call.data == '2':
                discord_channel_name = "элитная флудилка"
                discord_channel_id = 710240901137694800
            else:  # call.data == '3':
                discord_channel_name = "курилка"
                discord_channel_id = 777276267837915186

            bot.send_message(call.message.chat.id, "Отлично! Текущий канал: {}".format(discord_channel_name))

            # удаление встроенных кнопок
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=call.message.text,
                                  reply_markup=None)
    except Exception as e:
        print(repr(e))


@bot.message_handler(content_types=['text'])
def send_to_discord(message):
    try:
        path = "pipe.fifo"
        if not os.path.exists(path):
            os.mkfifo(path)

        try:
            first_name = message.from_user.first_name + ""  # По моей задумке, если у ползьзователя скрыт username,
            username = message.from_user.username + ""      # прибавление пустой строки поможет избежать ошибки
            print("Пользователь: \"{}@{}\". Текст: {}".format(first_name, username, message.text))
        except Exception as e:
            print(repr(e))

        pipe = open(path, "w")
        pipe.write(str(message.message_id) + '$space$' + message.text + "$space$" + str(discord_channel_id))
        pipe.close()
    except NameError:
        choose_discord_channel(message)


bot.polling()
