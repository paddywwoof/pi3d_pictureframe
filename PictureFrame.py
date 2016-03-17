#!/usr/bin/python

from __future__ import absolute_import, division, print_function, unicode_literals
"""This demo shows the use of special transition shaders on the Canvas 
shape for 2D drawing.
"""
import random, time, os, threading
# if pi3d isn't installed as a module then you will need..
import demo # only needed if pi3d not 'installed'. Does the same as..
import pi3d
import picture_getter

########################################################################
# set the user variables here
########################################################################
PIC_DIR = '/home/patrick/pi3d_pictureframe/pictures' # for filtering subdirectories
               # and file names alter lines c. 52 and 56 below
TMDELAY = 30.0  # time between slides This needs to be big enough for
               # texture loading and fading
FPS = 20       # animation frames per second
FADE_TM = 6.0  # time for fading
TK = False     # set to true to run in tk window (have to start x server)
MIPMAP = True  # whether to anti-alias map screen pixels to image pixels
               # set False if no scaling required (faster, less memory needed)
SHUFFLE = True # randomly shuffle the pictures
PPS = 3        # how many pictures to show before changing shader
CHKNUM = 30    # number of picture between re-loading file list
########################################################################
# Where the aspect ratio of the image is different from the monitor the
# gap is filled with a low alpha reflection of the image. If you want this
# to be the pure background then you can edit the file
# shaders/blend_include_fs.inc and change edge_alpha = 0.0
########################################################################

class Messages(object):
  def __init__(self):
    self.messages = []
    self.n_mess = 0
    self.i_mess = 0
    self.refresh_messages()

  def refresh_messages(self):
    with open('messages.txt', 'r') as f:
      self.messages = f.read().splitlines()
    self.n_mess = len(self.messages)
    self.i_mess = self.n_mess - 1 # reverse order - last email first

  def next_message(self):
    msg_split = self.messages[self.i_mess].split()
    self.i_mess -= 1
    if self.i_mess < 0:
      self.i_mess = self.n_mess - 1
    message = ''
    new_line = ''
    for word in msg_split:
      if len(new_line) > 80:
        message += '\n' + new_line
        new_line = ''
      new_line += word + ' '
    message += '\n' + new_line
    msg = pi3d.FixedString('FreeSans.ttf', message, font_size=32, background_color=(50,50,50,10),
            camera=CAMERA, shader=flatsh, f_type='SMOOTH')
    msg.sprite.position(0, (-msg.iy - DISPLAY.height)/2, 1.0)
    return msg
    
def tex_load(fname):
  ''' return a slide object
  '''
  slide = Slide()
  if not os.path.isfile(fname):
    return None
  tex = pi3d.Texture(fname, blend=True, mipmap=MIPMAP, m_repeat=True)
  xrat = DISPLAY.width/tex.ix
  yrat = DISPLAY.height/tex.iy
  if yrat < xrat:
    xrat = yrat
  wi, hi = tex.ix * xrat, tex.iy * xrat
  xi = (DISPLAY.width - wi)/2
  yi = (DISPLAY.height - hi)/2
  slide.tex = tex
  slide.dimensions = (wi, hi, xi, yi)
  return slide

def get_files():
  global SHUFFLE, PIC_DIR
  file_list = []
  extensions = ['.png','.jpg','.jpeg'] # can add to these
  for root, dirnames, filenames in os.walk(PIC_DIR):
      for filename in filenames:
          ext = os.path.splitext(filename)[1].lower()
          if ext in extensions and not 'water' in root and not filename.startswith('.'):
              file_list.append(os.path.join(root, filename)) 
  if SHUFFLE:
    random.shuffle(file_list) # randomize pictures
  else:
    file_list.sort() # if not suffled; sort by name
  return file_list, len(file_list) # tuple of file list, number of pictures

class Slide(object):
  def __init__(self):
    self.tex = None
    self.dimensions = None

# start background checking email inbox
email_param = {'run':True, 'freq':30.0}
t = threading.Thread(target=picture_getter.background_checker, args=(email_param,))
t.daemon = True
t.start()

# Setup display and initialise pi3d
DISPLAY = pi3d.Display.create(background=(0.3, 0.3, 0.3, 1.0),
                                frames_per_second=FPS, tk=TK)
if TK:
  win = DISPLAY.tkwin
  win.update()
else:
  mykeys = pi3d.Keyboard() # don't need this for picture frame but useful for testing
 
shader = [#pi3d.Shader("shaders/blend_star"),
          #pi3d.Shader("shaders/blend_holes"),
          pi3d.Shader("shaders/blend_false"),
          pi3d.Shader("shaders/blend_burn"),
          pi3d.Shader("shaders/blend_bump")
          ]
num_sh = len(shader)
flatsh = pi3d.Shader('uv_flat')

iFiles, nFi = get_files()
fade = 0.0
pic_num = nFi - 1

canvas = pi3d.Canvas()
canvas.set_shader(shader[0])

CAMERA = pi3d.Camera(is_3d=False)

pictr = 0 # to allow shader changing every PPS slides
shnum = 0 # shader number
nexttm = 0.0 # force next on first loop
fade_step = 1.0 / (FPS * FADE_TM)

sbg = tex_load(iFiles[pic_num]) # initially load a background slide

## load messages.txt
messages = Messages()
msg = messages.next_message()

while DISPLAY.loop_running():
  tm = time.time()
  if tm > nexttm: # load next image
    nexttm = tm + TMDELAY
    fade = 0.0 # reset fade to beginning
    sfg = sbg # foreground Slide set to old background
    pic_num = (pic_num + 1) % nFi # wraps to start
    if (pic_num % CHKNUM) == 0: # this will shuffle as well
      iFiles, nFi = get_files()
      pic_num = pic_num % nFi # just in case list is severly shortened
      messages.refresh_messages()
    tmp_slide = tex_load(iFiles[pic_num]) # background Slide load.
    if tmp_slide != None: # checking in case file deleted
      sbg = tmp_slide
    canvas.set_draw_details(canvas.shader,[sfg.tex, sbg.tex]) # reset two textures
    canvas.set_2d_size(sbg.dimensions[0], sbg.dimensions[1], sbg.dimensions[2], sbg.dimensions[3])
    canvas.unif[48:54] = canvas.unif[42:48] #need to pass shader dimensions for both textures
    canvas.set_2d_size(sfg.dimensions[0], sfg.dimensions[1], sfg.dimensions[2], sfg.dimensions[3])
    pictr += 1
    if pictr >= PPS:# shader change Pics Per Shader
      pictr = 0
      shnum = (shnum + 1) % num_sh
      canvas.set_shader(shader[shnum])

  if fade < 1.0:
    fade += fade_step # increment fade
    if fade > 1.0: # more efficient to test here than in pixel shader
      fade = 1.0
    canvas.unif[44] = fade # pass value to shader using unif list

  canvas.draw() # then draw it
  msg.draw()
  msg.sprite.translateY(0.2)
  if msg.sprite.y() > (msg.iy - DISPLAY.height) / 2 + 50:
    msg = messages.next_message()
    

  if TK:
    try:
      win.update() # needed if using tk
    except:
      DISPLAY.stop()
      try:
        win.destroy()
      except:
        pass
      break
    if win.ev == 'resized':
      DISPLAY.resize(win.winx, win.winy, win.width, win.height)
      win.resized = False
      win.ev = ''

  else:
    k = mykeys.read()
    if k==27: #ESC
      mykeys.close()
      DISPLAY.stop()
      break

email_param['run'] = False
DISPLAY.destroy()
