import os
import sys
import math
import random
import textwrap
from functions import *
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
    out_file = f"{timestamp}.gif"
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
        img.close()
        os.remove(file_path)
        return "format"
    img = img.convert('RGBA')
    high_on_potnuse = math.sqrt((img.width**2) + (img.height**2))
    border = round(high_on_potnuse/10)
    size = (img.width + border, img.height + border)
    shake_min = round((border/2) - (border/4))
    shake_max = round((border/2) + (border/4))
    try:
        for index in range(10):
            frame = Image.new('RGBA', size, color=(54, 57, 62, 255))
            offset = (random.randint(shake_min, shake_max), random.randint(shake_min, shake_max))
            frame.paste(img, offset, mask=img)
            frames.append(frame)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        out_file = f"{timestamp}.gif"
        out_path = os.path.join(sys.path[0], 'tmp', out_file)
        frames[0].save(out_path, format='GIF', optimize=True, append_images=frames[1:], duration=50, save_all=True, loop=0)
    except:
        out_path = "memory"
    finally:
        img.close()
        for frame in frames:
            frame.close()
        os.remove(file_path)
        return out_path

def inspiration(id, text, name):
    text = f"\"{text}\""
    name = f"- {name}"
    path = os.path.join(sys.path[0], 'images', 'inspire')
    files = os.listdir(path)
    files.remove(".gitkeep")
    file = random.choice(files)
    img = Image.open(os.path.join(path, file))
    draw = ImageDraw.Draw(img)
    high_on_potnuse = math.sqrt((img.width**2) + (img.height**2))
    font_size = round(high_on_potnuse / 30)
    font = ImageFont.truetype("impact.ttf", font_size)
    name_font = ImageFont.truetype("impact.ttf", round(font_size * .75))
    margin = round(high_on_potnuse/10)
    width = maximize_width(img, font, text, margin)
    width = equalize_width(img, font, text, width)
    text = textwrap.fill(text, width=width)
    border_width = round(high_on_potnuse / 1000)
    name_border_width = round(border_width * .75)
    text_size = draw.textsize(text=text, font=font)
    name_size = draw.textsize(text=name, font=name_font)
    x = (img.size[0]/2) - (text_size[0]/2)
    y = (img.size[1]/2) - (text_size[1]/2) - name_size[1]
    xy = (x, y)
    draw_text(img, text, xy, font, "center", "white", "black", border_width)
    x += text_size[0] - name_size[0]
    y += text_size[1] + name_size[1]
    xy = (x, y)
    draw_text(img, name, xy, name_font, "right", "white", "black", border_width)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    extension = file.split('.')[-1]
    out_file = f"{timestamp}_{id}.{extension}"
    out_path = os.path.join(sys.path[0], 'tmp', out_file)
    img.save(out_path)
    img.close()
    return out_path
    
def draw_text(img, text, xy, font, align, text_color, border_color, border_width):
    draw = ImageDraw.Draw(img)
    for angle in range(0, 360, 30):
        radians = math.radians(angle)
        x_offset = round(math.cos(radians) * border_width)
        y_offset = round(math.sin(radians) * border_width)
        xy_border = (x_offset + xy[0], y_offset + xy[1])
        draw.text(xy=xy_border, text=text, font=font, align=align, fill=border_color)
    draw.text(xy=xy, text=text, font=font, align=align, fill=text_color)
    return
    
def spongebob(ctx, message):
    border = 20
    bob = Image.open(os.path.join(sys.path[0], 'images', 'sponge.jpg'))
    draw = ImageDraw.Draw(bob)
    font = ImageFont.truetype("calibri.ttf", 30)
    author = f"{message.author.display_name}: {message.clean_content}"
    mocker = f"{ctx.author.display_name}: {spongify(message.clean_content)}"
    margin = 0
    author_width = maximize_width(bob, font, author, margin)
    mocker_width = maximize_width(bob, font, mocker, margin)
    text = [textwrap.fill(author, width=author_width), textwrap.fill(mocker, width=mocker_width)]
    text = "\n\n".join(text)
    size = draw.textsize(text=text, font=font)
    width = bob.width + (border * 2)
    height = bob.height + size[1] + (border * 3)
    img = Image.new('RGB', (width, height), color="white")
    offset = (border, size[1] + (border * 2))
    img.paste(bob, offset)
    draw = ImageDraw.Draw(img)
    offset = (border, border)
    draw.text(offset, text, font=font, fill="black")
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    out_file = f"{timestamp}.jpg"
    out_path = os.path.join(sys.path[0], 'tmp', out_file)
    img.save(out_path)
    img.close()
    return out_path

def maximize_width(img, font, text, margin):
    draw = ImageDraw.Draw(img)
    for i in range(1, len(text)):
        new_text = textwrap.fill(text, width=i)
        if draw.textsize(text=new_text, font=font)[0] > img.width - (margin * 2):
            return i - 1
    return i
    
def equalize_width(img, font, text, start_width):
    draw = ImageDraw.Draw(img)
    distances = []
    rows = len(textwrap.wrap(text, width=start_width))
    if rows < 2:
        return start_width
    for i in range(start_width, 1, -1):
        lines = textwrap.wrap(text, width=i)
        if len(lines) > rows:
            break
        widths = []
        for line in lines:
            width = draw.textsize(text=line, font=font)[0]
            widths.append(width)
        widths.sort()
        distance = abs(widths[0] - widths[-1])
        distances.append([i, distance])
    distances = sorted(distances, key=lambda x: x[1])
    return distances[0][0]
        
        
    