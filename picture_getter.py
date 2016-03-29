#!/usr/bin/env python
import email
import imaplib
import os
import time
from PIL import Image
# if STOP_FILE exists then this signals program shutdown (by crontab)
STOP_FILE = '/home/pi/pi3d_pictureframe/stop'

class FetchEmail():
  connection = None
  error = None

  def __init__(self, mail_server, username, password):
    self.connection = imaplib.IMAP4_SSL(mail_server)
    self.connection.login(username, password)
    self.connection.select(readonly=False) # so we can mark mails as read

  def close_connection(self):
    self.connection.close()

  def save_details(self, msg,  msg_file='/tmp/temp.txt', download_folder='/tmp'):
    """
    Given a message, save its attachments to the specified
    download folder (default is /tmp)
    """
    sender = self.parse_email_address(msg.get('From'))[0]
    date = msg.get('Date').split(':')
    date = date[0] + ':' + date[1]
    subject = msg.get('Subject')
    content = msg.get_payload()
    if msg.is_multipart():
      for part in content:
        typ = part.get('Content-Type')
        if 'text/plain' in typ:
          body = part.get_payload()
        elif 'image' in typ:
          filename = part.get_filename()
          att_path = os.path.join(download_folder, filename)
          if not os.path.isfile(att_path):
            with open(att_path, 'wb') as fp:
              fp.write(part.get_payload(decode=True))
            # check size and resize if > 1920
            im = Image.open(att_path)
            w = im.size[0]
            if w > 1920:
              rat = 1920.0 / w
              im.resize((int(im.size[0] * rat), int(im.size[1] * rat)), 
                               Image.BICUBIC).save(att_path, quality=95)
    else:
      body = content
    body = body.replace('\n',' ').replace('\r',' ').replace('  ',' ')
    with open(msg_file, 'a') as fp:
      fp.write('From {} {} {} ==> {}\n'.format(sender, date, subject, body))

  def fetch_unread_messages(self):
    emails = []
    (result, messages) = self.connection.search(None, 'UnSeen')
    if result == "OK":
      for message in messages[0].split():
        try: 
          ret, data = self.connection.fetch(message,'(RFC822)')
        except:
          print("No new emails to read.")
          self.close_connection()
          exit()

        msg = email.message_from_bytes(data[0][1])
        if isinstance(msg, str) == False:
          emails.append(msg)
        response, data = self.connection.store(message, '+FLAGS','\\Seen')

      return emails

    self.error = "Failed to retreive emails."
    return emails

  def parse_email_address(self, email_address):
    """
    Helper function to parse out the email address from the message
    return: tuple (name, address). Eg. ('John Doe', 'jdoe@example.com')
    """
    return email.utils.parseaddr(email_address)

def background_checker(param={'run':True, 'freq':60.0, 'news':False}):
  ''' this is designed to run in a thread so the params can be altered from
  the calling thread if they are in a dict object
  '''
  if os.path.exists(STOP_FILE):
    os.remove(STOP_FILE)
  while param['run']:
    fetcher = FetchEmail('your_email_server', 'your_email_address', 'your_email_password')
    msg_list = fetcher.fetch_unread_messages()
    for msg in msg_list:
      fetcher.save_details(msg, msg_file='/home/pi/pi3d_pictureframe/messages.txt',
                         download_folder='/home/pi/pi3d_pictureframe/pictures')
    if len(msg_list) > 0:
      param['news'] = True # signal that messages need reloading, after saving all
    fetcher.close_connection()
    if os.path.exists(STOP_FILE): # i.e. it's been added by cron to signal this app to stop
      param['run'] = False # use to signal to PictureFrame main loop
      break # might as well break now rather than wait till after sleep
    time.sleep(param['freq'])

