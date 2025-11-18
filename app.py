import streamlit as st
import genanki
import nltk
import requests
from gtts import gTTS
from deep_translator import GoogleTranslator
from nltk.corpus import wordnet as wn
import time, io, os, re
from PIL import Image, ImageDraw

# --- Cấu hình thư mục NLTK data để chạy trên Streamlit Cloud ---
nltk_data_dir = os.path.join(os.getcwd(), "nltk_data")
os.makedirs(nltk_data_dir, exist_ok=True)

nltk.data.path.append(nltk_data_dir)

# --- Tải dữ liệu NLTK nếu chưa có ---
if not os.path.exists(os.path.join(nltk_data_dir, "taggers", "averaged_perceptron_tagger")):
    nltk.download("averaged_perceptron_tagger", download_dir=nltk_data_dir)
if not os.path.exists(os.path.join(nltk_data_dir, "corpora", "wordnet")):
    nltk.download("wordnet", download_dir=nltk_data_dir)
if not os.path.exists(os.path.join(nltk_data_dir, "tokenizers", "punkt")):
    nltk.download("punkt", download_dir=nltk_data_dir)

# --- Hàm xác định loại từ ---
def pos_simple(tag):
    if tag.startswith("NN"): return "danh từ"
    if tag.startswith("VB"): return "động từ"
    if tag.startswith("JJ"): return "tính từ"
    if tag.startswith("RB"): return "trạng từ"
    return "khác"

def get_pos(word):
    pos = nltk.pos_tag([word])[0][1]
    return pos_simple(pos)

# --- Hàm lấy nghĩa tiếng Anh ---
def get_definition(word):
    syns = wn.synsets(word)
    return syns[0].definition() if syns else ""

# --- Hàm dịch sang tiếng Việt ---
def translate_word(word):
    try:
        return GoogleTranslator(source="en", target="vi").translate(word)
    except:
        return word

# --- Hàm lấy hình ảnh từ Wikipedia ---
def fetch_image(word):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "generator": "search",
        "gsrsearch": word,
        "gsrlimit": 1,
        "piprop": "thumbnail",
        "pithumbsize": 400,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json().get("query", {}).get("pages", {})
        for p in data.values():
            img = p.get("thumbnail", {}).get("source")
            if img:
                return requests.get(img, timeout=10).content
    except:
        pass

    # fallback: placeholder
    img = Image.new("RGB", (400, 250), (230,230,230))
    d = ImageDraw.Draw(img)
    d.text((20,100), word, fill=(0,0,0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

# --- Hàm tạo tên file an toàn ---
def safe_name(w): 
    return re.sub(r"[^a-z0-9]", "_", w.lower())

# --- Streamlit UI ---
st.title("🇬🇧 Auto Flashcard Generator (Python Web App)")
st.write("Dán danh sách từ vựng (mỗi dòng 1 từ) để tạo file .apkg (Anki).")

input_text = st.text_area("Nhập danh sách từ:", height=200)

if st.button("Generate Flashcards"):
    lines = [w.strip() for w in input_text.split("\n") if w.strip()]

    if len(lines) == 0:
        st.warning("Vui lòng nhập ít nhất 1 từ!")
    else:
        deck = genanki.Deck(100123, "Vocabulary Deck")
        media_files = []

        for i, word in enumerate(lines, 1):
            st.write(f"🔄 Đang xử lý {i}/{len(lines)}: **{word}**")

            # Xác định loại từ & nghĩa
            pos = get_pos(word)
            eng_def = get_definition(word)
            vi_def = translate_word(eng_def or word)

            # Lấy hình ảnh
            img_bytes = fetch_image(word)
            img_name = safe_name(word) + ".jpg"
            with open(img_name, "wb") as f:
                f.write(img_bytes)
            media_files.append(img_name)

            # Tạo âm thanh
            mp3_name = safe_name(word) + ".mp3"
            try:
                tts = gTTS(word)
                tts.save(mp3_name)
                media_files.append(mp3_name)
            except:
                mp3_name = ""

            # Nội dung front card
            front = f"<img src='{img_name}'/><br><b>{word}</b> <i>({pos})</i>"
            if mp3_name:
                front += f"<br>[sound:{mp3_name}]"

            back = vi_def

            deck.add_note(genanki.Note(
                model=genanki.BASIC_MODEL,
                fields=[front, back]
            ))

            time.sleep(0.2)  # tránh request quá nhanh

        # Tạo file .apkg
        package = genanki.Package(deck)
        package.media_files = media_files
        output_file = "flashcards.apkg"
        package.write_to_file(output_file)

        # Cho người dùng tải về
        with open(output_file, "rb") as f:
            st.download_button("⬇️ Download .apkg", f, file_name="flashcards.apkg")

        st.success("✅ Hoàn thành! Tải file flashcards và mở bằng Anki.")
