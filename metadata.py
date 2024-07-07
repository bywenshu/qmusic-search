from flask import Flask, request, jsonify, session
import requests
import os
import eyed3
from mutagen import File
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
import logging
import boto3
from botocore.exceptions import NoCredentialsError
from flask_cors import CORS
import time
import random
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于会话管理的密钥
CORS(app, resources={r"/process_song": {"origins": "*"}})  # 允许所有来源访问

# 配置日志
logging.basicConfig(level=logging.INFO)

# S3 配置
S3_REGION = 'xx-xxxx-x'
S3_ACCESS_KEY = 'xxxxxxxxxx'
S3_SECRET_KEY = 'xxxxxxxxxxxxxxxx'
S3_ENDPOINT = 'https://xx.xxxxxx.xxxx'

s3 = boto3.client('s3', endpoint_url=S3_ENDPOINT, region_name=S3_REGION,
                  aws_access_key_id=S3_ACCESS_KEY,
                  aws_secret_access_key=S3_SECRET_KEY)

def upload_to_s3(file_path, s3_bucket, s3_key):
    try:
        s3.upload_file(file_path, s3_bucket, s3_key)
        logging.info(f"File {file_path} uploaded to S3 bucket {s3_bucket} with key {s3_key}")
    except FileNotFoundError:
        logging.error("The file was not found")
        raise
    except NoCredentialsError:
        logging.error("Credentials not available")
        raise

def download_file(url, save_path):
    logging.info(f"Downloading file from {url}")
    url = url.replace('http://', 'https://')  # Ensure URL uses HTTPS
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        logging.info(f"File downloaded and saved to {save_path}")
    else:
        raise Exception(f"Failed to download file. Status code: {response.status_code}")

class MP3MetadataProcessor:
    def __init__(self, mp3_file):
        self.mp3_file = mp3_file
        self.audio = eyed3.load(mp3_file)
        
        if self.audio.tag is None:
            self.audio.initTag()

    def add_metadata(self, title, artist, lyrics_text, cover_image_file):
        # 添加标题和艺术家
        self.audio.tag.title = title
        self.audio.tag.artist = artist

        # 添加歌词
        self.audio.tag.lyrics.set(lyrics_text)

        # 添加封面图片
        with open(cover_image_file, 'rb') as img:
            self.audio.tag.images.set(3, img.read(), 'image/jpeg', u'Cover')

        self.audio.tag.save()
        logging.info("元数据已成功嵌入到MP3文件中")

def embed_lyrics_and_cover(audio_path, title, artist, lyrics, cover_url):
    logging.info(f"Embedding lyrics and cover into {audio_path}")
    audio = File(audio_path)
    
    if audio is None:
        raise Exception("Unsupported audio format")

    # 下载封面图片
    request_id = str(uuid.uuid4())
    cover_path = f"cover_{request_id}.jpg"
    cover_url = cover_url.replace('http://', 'https://')  # Ensure URL uses HTTPS
    download_file(cover_url, cover_path)

    if audio.mime[0] == 'audio/mp3':
        processor = MP3MetadataProcessor(audio_path)
        processor.add_metadata(title, artist, lyrics, cover_path)

    elif audio.mime[0] == 'audio/mp4':
        audio = MP4(audio_path)
        
        # 添加标题和艺术家
        audio["©nam"] = title
        audio["©ART"] = artist

        # 添加歌词
        audio["©lyr"] = lyrics

        # 添加封面图片
        with open(cover_path, 'rb') as albumart:
            audio.tags['covr'] = [
                MP4Cover(albumart.read(), imageformat=MP4Cover.FORMAT_JPEG)
            ]

        audio.save()

    elif audio.mime[0] == 'audio/flac':
        audio = FLAC(audio_path)
        
        # 添加标题和艺术家
        audio["title"] = title
        audio["artist"] = artist

        # 添加歌词
        audio["LYRICS"] = lyrics

        # 添加封面图片
        image = Picture()
        with open(cover_path, 'rb') as albumart:
            image.data = albumart.read()
        
        image.type = 3
        image.desc = 'Cover'
        image.mime = 'image/jpeg'
        audio.add_picture(image)

        audio.save()

    os.remove(cover_path)
    logging.info(f"Lyrics and cover embedded into {audio_path}")

@app.route('/process_song', methods=['POST'])
def process_song():
    data = request.json
    song_name = data['song_name']
    artist = data['artist']
    lyrics = data['lyrics'].replace("&apos;", "'").replace("&quot;", '"')
    cover_url = data['cover_url']
    music_url = data['music_url'].replace('http://', 'https://')  # Ensure URL uses HTTPS
    quality = data.get('quality', 'm4a')  # 默认为 'm4a' 质量

    # # 特定歌曲和歌手判断
    # if artist == 'Ed Sheeran' and song_name == 'Shape of You':
    #     logging.info("Skipping processing for 'Shape of You' by Ed Sheeran")
    #     return jsonify({"message": "Success", "file_path": "", "s3_url": "https://xxx.mp3"}), 200

    # 为每个用户请求生成唯一的文件路径
    request_id = str(uuid.uuid4())
    temp_music_file = f"music_{request_id}.tmp"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    music_file_path = os.path.join(current_dir, temp_music_file)

    try:
        logging.info("Processing song: %s by %s", song_name, artist)
        new_file_name = f"{song_name} - {artist}"
        
        # 检测文件格式
        download_file(music_url, music_file_path)
        audio = File(music_file_path)
        if audio is None:
            raise Exception("Unsupported audio format")

        if audio.mime[0] == 'audio/mp3':
            new_file_extension = 'mp3'
        elif audio.mime[0] == 'audio/mp4':
            new_file_extension = 'm4a'
        elif audio.mime[0] == 'audio/flac':
            new_file_extension = 'flac'
        else:
            raise Exception("Unsupported audio format")

        new_file_name = f"{new_file_name}.{new_file_extension}"
        new_file_path = os.path.join(current_dir, new_file_name)

        if os.path.exists(new_file_path):
            logging.info(f"File {new_file_name} already exists. Skipping creation.")
        else:
            # 嵌入歌词和封面图片
            embed_lyrics_and_cover(music_file_path, song_name, artist, lyrics, cover_url)
            os.rename(music_file_path, new_file_path)
            logging.info(f"File renamed to {new_file_path}")

        # 根据 quality 参数选择 S3 存储桶
        s3_bucket = {
            'm4a': 'xxxxx',
            '128': 'xxxxx-128',
            '320': 'xxxxx-320',
            'flac': 'xxxxx-flac'
        }.get(quality, 'Your Default Bucket') # 若 quality 参数异常，则使用的默认存储桶。

        # 上传到S3
        s3_key = new_file_name
        upload_to_s3(new_file_path, s3_bucket, s3_key)

        # 删除本地文件
        os.remove(new_file_path)
        logging.info(f"Local file {new_file_path} deleted after upload to S3")

        return jsonify({"message": "Success", "file_path": new_file_path, "s3_url": f"{S3_ENDPOINT}/{s3_bucket}/{s3_key}"}), 200
    except Exception as e:
        logging.error(f"Error processing song: {str(e)}")
        return jsonify({"message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3201)
