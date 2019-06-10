import io
import math
import random
import requests
import textwrap
from functions import *
from datetime import datetime
from PIL import Image, ImageFont, ImageDraw, ImageSequence

def shaky_text(text):
    frames = []
    frame = Image.new('RGBA', (1,1))
    draw = ImageDraw.Draw(frame)
    font_path = os.path.join(sys.path[0], "fonts", "whitney_medium.ttf")
    font = ImageFont.truetype(font_path, 15)
    text_size = draw.textsize(text=text, font=font)
    text_size = (text_size[0] + 5, text_size[1] + 10)
    for index in range(50):
        frame = Image.new('RGBA', text_size, color=(54, 57, 62, 255))
        draw = ImageDraw.Draw(frame)
        offset = (random.randint(0, 5), random.randint(3, 7))
        draw.text(offset, text, font=font, fill=(220, 221, 222, 255))
        frames.append(frame)
    output = io.BytesIO()
    output.name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.gif"
    frames[0].save(output, optimize=True, append_images=frames[1:], duration=50, save_all=True, loop=0)
    for frame in frames:
        frame.close()
    output.seek(0)
    return output

def shaky_image(file):
    frames = []
    try:
        img = Image.open(file)
    except OSError:
        img.close()
        return "format"
    img = img.convert('RGBA')
    high_on_potnuse = math.sqrt((img.width**2) + (img.height**2))
    border = round(high_on_potnuse/20)
    size = (img.width + border, img.height + border)
    shake_min = round((border/2) - (border/4))
    shake_max = round((border/2) + (border/4))
    try:
        for index in range(10):
            frame = Image.new('RGBA', size, color=(54, 57, 62, 255))
            offset = (random.randint(shake_min, shake_max), random.randint(shake_min, shake_max))
            frame.paste(img, offset, mask=img)
            frames.append(frame)
        output = io.BytesIO()
        output.name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.gif"
        frames[0].save(output, optimize=True, append_images=frames[1:], duration=50, save_all=True, loop=0)
        output.seek(0)
    except:
        output = "memory"
    finally:
        img.close()
        for frame in frames:
            frame.close()
        return output

def get_unsplash(query):
    try:
        config = load_yaml("config.yaml")
        client_id = config["api"]["unsplash"]
        url = "https://api.unsplash.com/photos/random"
        params = {
            "client_id" : client_id,
            "query" : query
        }
        r = requests.get(url, params=params)
        if r.status_code != 200:
            params = {
                "client_id" : client_id,
            }
            r = requests.get(url, params=params)
        url = r.json()["links"]["download"]
        author = str(r.json()["user"]["name"])
        author = f"{author} on Unsplash"
        r = requests.get(url)
        img = Image.open(io.BytesIO(r.content))
        return img, author
    except:
        return None, None

def get_chromecast(query):
    try:
        url = "https://raw.githubusercontent.com/dconnolly/chromecast-backgrounds/master/backgrounds.json"
        r = requests.get(url)
        matches = []
        all_images = []
        for image in r.json():
            image_url = image["url"]
            image_author = None
            if "author" in image:
                image_author = image["author"]
            potential_match = [image_url, image_author]
            if query != None:
                if query in image_url.lower():
                    matches.append(potential_match)
            all_images.append(potential_match)
        if len(matches) > 0:
            choice = random.choice(matches)
        else:
            choice = random.choice(all_images)
        url = choice[0]
        author = choice[1]
        r = requests.get(url)
        img = Image.open(io.BytesIO(r.content))
        return img, author
    except:
        return None, None

def get_local():
    try:
        path = os.path.join(sys.path[0], 'images', 'inspire')
        files = os.listdir(path)
        files.remove(".gitkeep")
        file = random.choice(files)
        img = Image.open(os.path.join(path, file))
        return img, None
    except:
        return None, None

def inspiration(id, text, name, query, comical):
    text = ascii_only(f"\"{text}\"")
    name = ascii_only(f"- {name}")
    if chance(50):
        img, author = get_unsplash(query)
        if img == None:
            img, author = get_chromecast(query)
            if img == None:
                img, author = get_local()
                if img == None:
                    return None
    else:
        img, author = get_chromecast(query)
        if img == None:
            img, author = get_unsplash(query)
            if img == None:
                img, author = get_local()
                if img == None:
                    return None
    draw = ImageDraw.Draw(img)
    high_on_potnuse = math.sqrt((img.width**2) + (img.height**2))
    font_size = round(high_on_potnuse / 25)
    if comical and chance(config["chance"]["comical"]):
        font = ImageFont.truetype("comic.ttf", font_size)
        name_font = ImageFont.truetype("comic.ttf", round(font_size * .75))
    else:
        font = ImageFont.truetype("impact.ttf", font_size)
        name_font = ImageFont.truetype("impact.ttf", round(font_size * .75))
    margin = round(high_on_potnuse/10)
    width = maximize_width(img, font, text, margin)
    width = equalize_width(img, font, text, width)
    text = textwrap.fill(text, width=width)
    border_width = round(high_on_potnuse / 750)
    name_border_width = round(border_width * .75)
    attribution_border_width = round(border_width * .25)
    text_size = draw.textsize(text=text, font=font)
    name_size = draw.textsize(text=name, font=name_font)
    x = (img.width/2) - (text_size[0]/2)
    y = (img.height/2) - (text_size[1]/2) - name_size[1]
    xy = (x, y)
    draw_text(img, text, xy, font, "center", "white", "black", border_width)
    x += text_size[0] - name_size[0]
    y += text_size[1] + name_size[1]
    xy = (x, y)
    draw_text(img, name, xy, name_font, "right", "white", "black", name_border_width)
    if author != None:
        attribution = ascii_only(f"Photo by {author}")
        attribution_font = ImageFont.truetype("arial.ttf", round(font_size * .25))
        attribution_size = draw.textsize(text=attribution, font=attribution_font)
        x = img.width - attribution_size[0] - attribution_size[1]
        y = img.height - attribution_size[1] - attribution_size[1]
        xy = (x, y)
        draw.text(xy=xy, text=attribution, font=attribution_font, align="right", fill="gray")
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    output = io.BytesIO()
    output.name = f"{timestamp}_{id}.jpg"
    img.save(output)
    while output.getbuffer().nbytes > 8000000:
        ratio = 0.9
        output = io.BytesIO()
        output.name = f"{timestamp}_{id}.png"
        new_size = (int(img.width*ratio), int(img.height*ratio))
        img.thumbnail(new_size, resample=Image.ANTIALIAS)
        img.save(output)
    img.close()
    output.seek(0)
    return output

def sunny(text):
    img = Image.new('RGB', (3840, 2160))
    draw = ImageDraw.Draw(img)
    font_path = os.path.join(sys.path[0], "fonts", "textile_regular.ttf")
    font = ImageFont.truetype(font_path, 100)
    width = maximize_width(img, font, text, 250)
    width = equalize_width(img, font, text, width)
    text = textwrap.fill(text, width=width)
    text_size = draw.textsize(text=text, font=font)
    x = (img.size[0]/2) - (text_size[0]/2)
    y = (img.size[1]/2) - (text_size[1]/2)
    xy = (x, y)
    draw.text(xy=xy, text=text, font=font, align="center", fill="white")
    output = io.BytesIO()
    output.name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    img.save(output)
    output.seek(0)
    return output

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
    font = ImageFont.truetype("arial.ttf", 30)
    author = ascii_only(f"{message.author.display_name}: {message.clean_content}")
    mocker = ascii_only(f"{ctx.author.display_name}: {spongify(message.clean_content)}")
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
    output = io.BytesIO()
    output.name = f"{timestamp}.jpg"
    img.save(output)
    img.close()
    output.seek(0)
    return output

def maximize_width(img, font, text, margin):
    draw = ImageDraw.Draw(img)
    for i in range(1, len(text) + 1):
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

