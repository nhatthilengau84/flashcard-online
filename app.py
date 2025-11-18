import streamlit as st
import genanki
import nltk
import requests
from gtts import gTTS
from googletrans import Translator
from nltk.corpus import wordnet as wn
import time, io, os, re
from PIL import Image, ImageDraw

# Tải dữ liệu NLTK nếu chưa có
nltk.download("punkt")
nltk.download("averaged_perceptron_tagger")
nltk.download("wordnet")

translator = Translator()

def pos_simple(tag):
    if tag.startswith("NN"): return "danh từ"
    if tag.startswith("VB"): return "động từ"
    if tag.startswith("JJ"): return "tính từ"
    if tag.startswith("RB"): return "trạng từ"
    return "khác"

def get_pos(word):
    pos = nltk.pos_tag([word])[0][1]
    return pos_simple(pos)

def get_definition(word):
    syns = wn.synsets(word)
    return syns[0].definition() if syns else ""

def translate_vi(text):
    try:
        return translator.translate(text, dest='vi').text
    except:
        return text

def fetch_image(word):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query","format": "json","prop": "pageimages",
        "generator": "search","gsrsearch": word,"gsrlimit": 1,
        "piprop": "thumbnail","pithumbsize": 400,
    }
    try:
        r = requests.get(url, params=params)
        data = r.json().get("query", {}).get("pages", {})
        for p in data.values():
            img = p.get("thumbnail", {}).get("source")
            if img:
                return requests.get(img).content
    except:
        pass

    # fallback: placeholder
    img = Image.new("RGB", (400, 250), (230,230,230))
    d = ImageDraw.Draw(img)
    d.text((20,100), word, fill=(0,0,0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def safe_name(w): return re.sub(r"[^a-z0-9]", "_", w.lower())

st.title("🇬🇧 Auto Flashcard Generator (Python Web App)")
st.write("Dán danh sách từ vựng để tạo file .apkg (Anki).")

input_text = st.text_area("Nhập danh sách từ (mỗi dòng 1 từ):", height=200)

if st.button("Generate Flashcards"):
    lines = [w.strip() for w in input_text.split("\n") if w.strip()]

    deck = genanki.Deck(100123, "Vocabulary Deck")
    media_files = []

    for i, word in enumerate(lines, 1):
        st.write(f"🔄 Đang xử lý {i}/{len(lines)}: **{word}**")

        pos = get_pos(word)
        eng_def = get_definition(word)
        vi_def = translate_vi(eng_def or word)

        img_bytes = fetch_image(word)
        img_name = safe_name(word) + ".jpg"
        with open(img_name, "wb") as f:
            f.write(img_bytes)
        media_files.append(img_name)

        mp3_name = safe_name(word) + ".mp3"
        try:
            tts = gTTS(word)
            tts.save(mp3_name)
            media_files.append(mp3_name)
        except:
            mp3_name = ""

        front = f"<img src='{img_name}'/><br><b>{word}</b> <i>({pos})</i>"
        if mp3_name:
            front += f"<br>[sound:{mp3_name}]"

        back = vi_def

        deck.add_note(genanki.Note(
            model=genanki.BASIC_MODEL,
            fields=[front, back]
        ))

        time.sleep(0.2)

    package = genanki.Package(deck)
    package.media_files = media_files
    output_file = "flashcards.apkg"
    package.write_to_file(output_file)

    with open(output_file, "rb") as f:
        st.download_button("⬇️ Download .apkg", f, file_name="flashcards.apkg")
