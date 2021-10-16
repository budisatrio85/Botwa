import time
import requests
import json
import re
import sqlite3
import os
import sys
import importlib
from datetime import datetime
from datetime import timedelta
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
thismodule = sys.modules[__name__]



# open config
config = {}
with open("config.json") as json_data_file:
    config = json.load(json_data_file)

def focus(contact):
    # cari kontak
    user = wa_driver.find_element_by_xpath(config['chat_xpath']['contact'].format(contact))
    user.click()

def send_chat(contact, text):
    try:
        # cari kontak
        focus(contact)
        
        # send text
        text_box = wa_driver.find_element_by_xpath(config['chat_xpath']['textbox'])
        time.sleep(1)
        text_box.send_keys(text + Keys.ENTER)
        time.sleep(1)
    except Exception as e:
        print('send_chat ' + str(e))
        wa_driver.get("https://web.whatsapp.com")
        time.sleep(5)

def send_chat_with_image(contact, text, arr_image_path):
    try:
        # cari kontak
        focus(contact)

        # tempel arr_image_path ke 1
        attachment = wa_driver.find_element_by_xpath(config['chat_xpath']['attachment'])
        attachment.click()
        input_image = wa_driver.find_element_by_xpath(config['chat_xpath']['image_1'])
        image_path=os.path.abspath(arr_image_path[0])
        input_image.send_keys(arr_image_path[0])
        time.sleep(1)
        
        i = 1
        while i < len(arr_image_path):
            input_image = wa_driver.find_element_by_xpath(config['chat_xpath']['image_n'])
            image_path=os.path.abspath(arr_image_path[i])
            input_image.send_keys(image_path)    
            time.sleep(1)
            i = i+1
        
        # send text
        text_box = wa_driver.find_element_by_xpath(config['chat_xpath']['textbox_with_attachment'])
        text_box.send_keys(text + Keys.ENTER)
        time.sleep(1)
    except Exception as e:
        print('send_chat_image ' + str(e))
        wa_driver.get("https://web.whatsapp.com")
        time.sleep(5)

def parse_and_execute(list_command,message,contact_name):
    message_words = message.lower().split(" ")
    result = "Mohon maaf saya belum mengerti maksudnya, mohon kontak "+config['contact_no']
    for i,command in enumerate(list_command):
        set_command = set(command[0].split(" "))
        set_words = set(message_words)
        if set_command.issubset(set_words):
            date_string = datetime.now().strftime("%d-%m-%Y")
            try:
                for file in os.listdir("plugins"):
                    if file.endswith(".py"):
                        plugins_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "plugins"))

                        # import plugin
                        sys.path.insert(0, plugins_path)
                        module = importlib.import_module(os.path.splitext(file)[0])
                        result = getattr(module, command[1])(date_string,message,contact_name) 
                        return result
            except Exception as e:
                print(e)
    return result

def process_message(contact_group,contact_name,contact_message,contact_date_str):
    global queue_messages
    conn = sqlite3.connect(config['db_location'])
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (contact_name,contact_message,contact_group,contact_date_str,created_at,status) VALUES (?,?,?,?,?,0)",[contact_name,contact_message,contact_group,contact_date_str,datetime.now()])
    c.execute("SELECT command_words,method FROM command_list")
    data=c.fetchall()
    conn.commit()

    print("Processing: " + contact_message)
    try:
        message_full = ""+ Keys.ALT + Keys.ENTER
        image_path = ""
        if config['contact_tag'] in contact_message:
            message_full = "Hi "+contact_group+': '+ Keys.ALT + Keys.ENTER
        hasil = parse_and_execute(data,contact_message,contact_name)
        if '.png' in hasil:
            image_path = hasil
            hasil = 'Berikut adalah tampilannya'+ Keys.ALT + Keys.ENTER
            message_full += hasil + Keys.ALT
            c = conn.cursor()
            c.execute("INSERT INTO chat_reply (contact_name,contact_message,contact_group,contact_date_str,created_at,status, image) VALUES (?,?,?,?,?,0,?)",[contact_name,message_full,contact_group,contact_date_str,datetime.now(),image_path])
        else:
            message_full += hasil + Keys.ALT
            c = conn.cursor()
            c.execute("INSERT INTO chat_reply (contact_name,contact_message,contact_group,contact_date_str,created_at,status) VALUES (?,?,?,?,?,0)",[contact_name,message_full,contact_group,contact_date_str,datetime.now()])
    except Exception as e:
        print(e) 
        message_full = "Mohon maaf bot sedang berkebun sejenak"
        c = conn.cursor()
        c.execute("INSERT INTO chat_reply (contact_name,contact_message,contact_group,contact_date_str,created_at,status) VALUES (?,?,?,?,?,0)",[contact_name,message_full,contact_group,contact_date_str,datetime.now()])
    finally:
        conn.commit()
        conn.close()

def send_messages():
    conn = sqlite3.connect(config['db_location'])
    c = conn.cursor()
    c.execute("SELECT id,contact_name,contact_message,image FROM chat_reply WHERE status = 0 ORDER BY created_at ASC")
    data=c.fetchall()
    try:
        for row in data:
            print("Sending to "+row[1]+" : "+row[2])
            if row[3] != None:
                send_chat_with_image(row[1], row[2], row[3])
            else:
                send_chat(row[1], row[2])
            c.execute('UPDATE chat_reply SET status = 1 WHERE id = ?',[row[0]])
        if len(data)>0:
            send_chat('Null','y')
    except Exception as e:
        print(e) 
    finally:
        conn.commit()
        conn.close()       
        focus('Null')

def read_messages(contact_name):
    # ambil dari db
    conn = sqlite3.connect(config['db_location'])
    c = conn.cursor()
    c.execute("SELECT contact_name,contact_message,contact_group,contact_date_str,created_at FROM chat_history WHERE contact_name = ? ORDER BY created_at DESC LIMIT 100", [contact_name])
    data=c.fetchall() 
    conn.commit()
    conn.close()

    contact_from = contact_name
    new_insert = False
    print(' baca message dari = '+contact_name)

    # cek apakah ada more message
    objChat = wa_driver.find_elements_by_xpath(config['thread_xpath']['start_message'])
    index_chat_more_message = len(objChat)
    
    # cek jumlah message saat buka
    xpath_num_message = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div'
    objChat = wa_driver.find_elements_by_xpath(xpath_num_message)
    len_chat = len(objChat)

    if len_chat == 0:
        # cek total
        index_chat_more_message = index_chat_more_message - 1
        xpath_num_message = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div'
        objChat = wa_driver.find_elements_by_xpath(xpath_num_message)
        len_chat = len(objChat)

        if len_chat == 0:
            # cek total
            index_chat_more_message = index_chat_more_message - 1
            xpath_num_message = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div'
            objChat = wa_driver.find_elements_by_xpath(xpath_num_message)
            len_chat = len(objChat)
    print(" jumlah message = "+str(len(objChat)))

    for item_message in range(2,len_chat+1,1):   
        try:
            # cek apakah message-in / message-out
            xpath_message_in = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']'
            type_message = wa_driver.find_element_by_xpath(xpath_message_in).get_attribute('class')
            if 'message-in' in type_message:

                # cek apakah message / info
                xpath_message_info = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/span'
                objChat = wa_driver.find_element_by_xpath(xpath_message_info)
                if objChat.text == "":

                    # cek apakah group / personal
                    xpath_jumlah_div_pesan = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div/div'
                    jml_div = wa_driver.find_elements_by_xpath(xpath_jumlah_div_pesan)
                    div_message = 1
                    div_contact = 0
                    add_div_image = ""

                    # kalau ada 1, berarti ada gambarnya
                    if len(jml_div) == 1:
                        xpath_jumlah_div_pesan = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div/div/div'
                        jml_div = wa_driver.find_elements_by_xpath(xpath_jumlah_div_pesan)
                        add_div_image = "/div"

                    # kalau ada 4: kontak, gambar/link/reply, pesan, waktu
                    if len(jml_div) == 4:
                        div_contact = 1
                        div_message = 3

                    # kalau ada 3: kontak, pesan, waktu
                    if len(jml_div) == 3:
                        div_contact = 1
                        div_message = 2
   
                    # kalau ada 2: pesan, waktu
                    if(len(jml_div) == 2):
                        div_contact = 0
                        div_message = 1
                    
                    # kalau ada contact
                    if div_contact>0:

                        # cek apakah ada extra div
                        xpath_div_contact = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div/div'
                        extra_div_elem = wa_driver.find_element_by_xpath(xpath_div_contact)
                        extra_div = extra_div_elem.get_attribute('class')
                        has_extra_div = ""
                        if extra_div == "":
                            has_extra_div = "/div"

                        # cek apakah contact sudah save belum
                        xpath_div_contact = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div'+add_div_image+'/div['+str(div_contact)+']'+has_extra_div+'/span'
                        jml_div_contact = wa_driver.find_elements_by_xpath(xpath_div_contact)
                        div_saved_contact = len(jml_div_contact)

                        # ambil contact (nomor / saved contact)
                        xpath_div_contact = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div'+add_div_image+'/div['+str(div_contact)+']'+has_extra_div+'/span[1]'
                        isi_div_contact = wa_driver.find_element_by_xpath(xpath_div_contact)
                        if isi_div_contact.text == "Forwarded":
                            contact_from = contact_name
                        else:
                            contact_from = isi_div_contact.text

                        # ambil nama
                        if div_saved_contact > 1:
                            xpath_div_contact = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div'+add_div_image+'/div['+str(div_contact)+']'+has_extra_div+'/span['+str(div_saved_contact)+']'
                            isi_div_contact = wa_driver.find_element_by_xpath(xpath_div_contact)
                            if isi_div_contact.text == "Forwarded":
                                contact_from = contact_name
                            else:
                                contact_from += ' '+isi_div_contact.text

                    # ambil message
                    xpath_message = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div'+add_div_image+'/div['+str(div_message)+']/div/span[1]/span'
                    contact_message = wa_driver.find_element_by_xpath(xpath_message).text
                    
                    # ambil time
                    xpath_message_time = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div'+add_div_image+'/div['+str(div_message)+']'
                    contact_time = wa_driver.find_element_by_xpath(xpath_message_time)
                    contact_time_fulldate = str(contact_time.get_attribute('data-pre-plain-text'))

                    # kalau ada gambar / quote
                    if contact_time_fulldate == 'None':
                        xpath_message_time = config['thread_xpath']['start_message']+'['+str(index_chat_more_message)+']/div['+str(item_message)+']/div/div/div'
                        contact_time = wa_driver.find_element_by_xpath(xpath_message_time)
                        contact_time_fulldate = str(contact_time.get_attribute('data-pre-plain-text'))
                    contact_time_fulldate_string = re.search(r"\[(.*?)\]", contact_time_fulldate).group(1)
                    
                    # fix date
                    if '24:' in contact_time_fulldate_string:
                        contact_time_fulldate_string = contact_time_fulldate_string.replace('24:','00:')
                    
                    if len(data)==0 and not new_insert:

                        # kalau belum ada di db
                        new_insert = True
                        process_message(contact_from, contact_name, contact_message, contact_time_fulldate_string)
                    else:

                        # kalau sudah ada di db
                        time_text = datetime.now()
                        try:
                            time_text = datetime.strptime(contact_time_fulldate_string, '%H:%M, %d/%m/%Y') 
                        except Exception as e:
                            time_text = datetime.strptime(contact_time_fulldate_string, '%I:%M %p, %d/%m/%Y') 
                        try:
                            time_last_saved_string = list(data[0])[3]
                            time_last_saved = datetime.strptime(time_last_saved_string, '%H:%M, %d/%m/%Y')
                        except Exception as e:
                            time_last_saved_string = list(data[0])[3]
                            time_last_saved = datetime.strptime(time_last_saved_string, '%I:%M %p, %d/%m/%Y')

                        # ambil yang waktu terbaru
                        if time_text >= time_last_saved:
                            data_per_waktu = list(filter(lambda x: x[3]==time_last_saved_string, data))
                            jml_data = len(data_per_waktu)
                            is_data_exist = False
                            for idx in range(0,jml_data,1): 
                                name_check = data_per_waktu[idx][0]
                                message_check = data_per_waktu[idx][1]
                                from_check = data_per_waktu[idx][2]
                                time_check = data_per_waktu[idx][3]
                                if name_check == contact_name and message_check == contact_message and from_check == contact_from and time_check == contact_time_fulldate_string:
                                    is_data_exist = True
                            if not is_data_exist:
                                process_message(contact_from, contact_name, contact_message, contact_time_fulldate_string)
                    
        except Exception as e:
            print(e) 
    try:
        focus('Null')
    except Exception as e:
        print(e) 
        time.sleep(5) 

def get_messages():
    try:
        objChat = wa_driver.find_elements_by_xpath(config['thread_xpath']['number_chat'])
        len_chat = len(objChat)
        for item in range(len_chat,0,-1):      
            xpath_num_notif = config['thread_xpath']['number_chat']+'['+str(item)+']'+config['thread_xpath']['number_notification']
            objChat = wa_driver.find_element_by_xpath(xpath_num_notif)
            len_notif = objChat.text
            if len_notif != "":   
                print(" ada notif = "+str(len_notif))                  
                xpath_name = config['thread_xpath']['number_chat']+'['+str(item)+']'+config['thread_xpath']['contact_name']
                contact_name = wa_driver.find_element_by_xpath(xpath_name)
                if contact_name.get_attribute('title') == "":
                    xpath_name = config['thread_xpath']['number_chat']+'['+str(item)+']'+config['thread_xpath']['contact_name_group']
                    contact_name = wa_driver.find_element_by_xpath(xpath_name)   

                xpath_notif = config['thread_xpath']['number_chat']+'['+str(item)+']'+config['thread_xpath']['each_thread']
                objChat = wa_driver.find_element_by_xpath(xpath_notif)
                objChat.click()
                time.sleep(1)
                
                read_messages(contact_name.get_attribute('title'))
        send_messages()
    except Exception as e:
        print('get_messages ' + str(e))
        #wa_driver.get("https://web.whatsapp.com")
        time.sleep(5)

chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--dns-prefetch-disable")
chrome_options.add_argument("--disable-gpu")
wa_driver = webdriver.Chrome(ChromeDriverManager().install(),chrome_options=chrome_options)

while True:
    try:
        wa_driver.get("https://web.whatsapp.com")
        print("==============================")
        print("Scan QR Code, then press Enter")
        print("==============================")
        input()
        
        while True:
            # auto listening
            get_messages()

            # !! contoh send manual
            # send_chat('+62 812-9566-8925','Hello')

            # tunggu 
            time.sleep(config['sleep_seconds'])

            # !! kalau belum join beta, perlu refresh biar stabil
            # if (datetime.today().timestamp() % config['refresh_every'])<1:
            #    wa_driver.refresh()
            #    time.sleep(5)
    except Exception as e:
        print('main_loop ' + str(e))
        wa_driver.quit()
        wa_driver = webdriver.Chrome(ChromeDriverManager().install())
