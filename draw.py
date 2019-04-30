import os
import sys
import math
import random
import textwrap
from datetime import datetime
from PIL import Image, ImageFont, ImageDraw

def shaky_text(text):
    frames = []
    frame = Image.new('RGBA', (1,1))
    draw = ImageDraw.Draw(frame)
    font = ImageFont.truetype("arial.ttf", 15)
    text_size = draw.textsize(text=text, font=font)
    text_size = (text_size[0] + 5, text_size[1] + 10)
    for index in range(50):
        frame = Image.new('RGBA', text_size, color=(54, 57, 62, 255))
        draw = ImageDraw.Draw(frame)
        offset = (random.randint(0, 5), random.randint(3, 7))
        draw.text(offset, text, font=font, fill=(255, 255, 255, 255))
        frames.append(frame)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    out_file = "{}.gif".format(timestamp)
    out_path = os.path.join(sys.path[0], 'tmp', out_file)
    frames[0].save(out_path, format='GIF', optimize=True, append_images=frames[1:], duration=50, save_all=True, loop=0)
    for frame in frames:
        frame.close()
    return out_path
    
def shaky_image(file_path):
    frames = []
    try:
        img = Image.open(file_path)
    except OSError:
        return None
    img = img.convert('RGBA')
    high_on_potnuse = math.sqrt((img.width**2) + (img.height**2))
    border = int(high_on_potnuse/10)
    size = (img.width + border, img.height + border)
    shake_min = int((border/2) - (border/4))
    shake_max = int((border/2) + (border/4))
    for index in range(50):
        frame = Image.new('RGBA', size, color=(54, 57, 62, 255))
        offset = (random.randint(shake_min, shake_max), random.randint(shake_min, shake_max))
        frame.paste(img, offset, mask=img)
        frames.append(frame)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    out_file = "{}.gif".format(timestamp)
    out_path = os.path.join(sys.path[0], 'tmp', out_file)
    frames[0].save(out_path, format='GIF', optimize=True, append_images=frames[1:], duration=50, save_all=True, loop=0)
    img.close()
    for frame in frames:
        frame.close()
    return out_path

def inspiration(id, text, name):
    text = '\"' + text + '\"'
    name = '- ' + name
    path = os.path.join(sys.path[0], 'images', 'inspire')
    files = os.listdir(path)
    file = random.choice(files)
    img = Image.open(os.path.join(path, file))
    draw = ImageDraw.Draw(img)
    img_size = img.size
    font_size = int(((img.width + img.height) / 2) / 15)
    line_width = int(img.width / (font_size * .5))
    font = ImageFont.truetype("impact.ttf", font_size)
    border = int(((img.width + img.height) / 2) / 768)
    multi_line = ""
    for line in textwrap.wrap(text, width=line_width):
        multi_line += line + "\n"
    text_size = draw.multiline_textsize(text=multi_line, font=font)
    name_size = draw.textsize(text=name, font=font)
    x = (img_size[0]/2) - (text_size[0]/2)
    y = (img_size[1]/2) - (text_size[1]/2) - name_size[1]
    draw.multiline_text((x-border,y),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x-border,y-border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x,y-border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x+border,y-border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x+border,y),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x+border,y+border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x,y+border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x-border,y+border),multi_line,font=font, align='center', fill='black')
    draw.multiline_text((x,y),multi_line,font=font, align='center', fill='white')
    x += text_size[0] - name_size[0]
    y += text_size[1]
    draw.text((x-border,y),name,font=font, align='right', fill='black')
    draw.text((x-border,y-border),name,font=font, align='right', fill='black')
    draw.text((x,y-border),name,font=font, align='right', fill='black')
    draw.text((x+border,y-border),name,font=font, align='right', fill='black')
    draw.text((x+border,y),name,font=font, align='right', fill='black')
    draw.text((x+border,y+border),name,font=font, align='right', fill='black')
    draw.text((x,y+border),name,font=font, align='right', fill='black')
    draw.text((x-border,y+border),name,font=font, align='right', fill='black')
    draw.text((x,y),name,font=font, align='right', fill='white')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    extension = file.split('.')[-1]
    out_file = "{}_{}.{}".format(timestamp, id, extension)
    out_path = os.path.join(sys.path[0], 'tmp', out_file)
    img.save(out_path)
    img.close()
    return out_path