# Botwa
Whatsapp processor using Selenium.
Works by searching xpath of whatsapp web, process messages, then save chat history to db
Open for plugins!

## Config
Change db location and contact no

## Database
Botwa uses SQLite, with some tables:
1. chat_history : for saving incoming messages
2. chat_reply : for saving sent replies
3. command_list : for translating words into commands

## How to use
0. Create group called 'Null' -> this is for anchoring message
1. Run main.py
2. In the browser, login to your whatsapp using QR
3. Press enter in the console
4. Botwa will process the message

## Plugins
1. Put your python file inside 'plugins' folder
2. Create function with 3 parameters: date string, chat message, contact name (example provided)
2. Register your function name on command_list table: insert into command_list(command_words,method) values (your_command_words,your_function_name)

## Tips
Please use multi-device beta, so that you won't have to monitor whatsapp status on your phone
