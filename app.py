from flask import Flask, request, render_template, session, redirect, url_for, jsonify
import requests
import time
import json
import Main
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 生成一个随机密钥用于会话

# 初始化QQ音乐对象
QQM = Main.QQ_Music()
cookie_str = '[Cookies 填写在这里。]'
QQM._cookies = QQM.set_cookie(cookie_str)

class QQMusic:
    def __init__(self):
        self.base_url = 'https://u.y.qq.com/cgi-bin/musicu.fcg'
        self.guid = '10000'
        self.uin = '0'
        self.cookies = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        self.file_config = {
            'm4a': {'s': 'C400', 'e': '.m4a', 'bitrate': 'M4A'},
            '128': {'s': 'M500', 'e': '.mp3', 'bitrate': '128kbps'},
            '320': {'s': 'M800', 'e': '.mp3', 'bitrate': '320kbps'},
            'flac': {'s': 'F000', 'e': '.flac', 'bitrate': 'FLAC'},
        }

    def set_cookies(self, cookie_str):
        cookies = {}
        for cookie in cookie_str.split('; '):
            key, value = cookie.split('=', 1)
            cookies[key] = value
        self.cookies = cookies

    def get_music_url(self, songmid, file_type='128'):
        """
        获取音乐播放URL

        参数:
        songmid: str - 歌曲的MID
        file_type: str - 音质类型，可选参数：'m4a', '128', '320', 'flac'

        返回:
        dict - 包含音乐播放URL和比特率的字典
        """
        if file_type not in self.file_config:
            raise ValueError("Invalid file_type. Choose from 'm4a', '128', '320', 'flac'")

        file_info = self.file_config[file_type]
        file = f"{file_info['s']}{songmid}{songmid}{file_info['e']}"

        req_data = {
            'req_1': {
                'module': 'vkey.GetVkeyServer',
                'method': 'CgiGetVkey',
                'param': {
                    'filename': [file],
                    'guid': self.guid,
                    'songmid': [songmid],
                    'songtype': [0],
                    'uin': self.uin,
                    'loginflag': 1,
                    'platform': '20',
                },
            },
            'loginUin': self.uin,
            'comm': {
                'uin': self.uin,
                'format': 'json',
                'ct': 24,
                'cv': 0,
            },
        }

        response = requests.post(self.base_url, json=req_data, cookies=self.cookies, headers=self.headers)
        data = response.json()

        purl = data['req_1']['data']['midurlinfo'][0]['purl']
        if purl == '':
            # VIP
            return None

        url = data['req_1']['data']['sip'][0] + purl
        prefix = purl[:4]
        bitrate = next((info['bitrate'] for key, info in self.file_config.items() if info['s'] == prefix), '')

        return {'url': url, 'bitrate': bitrate}

def replace_http_with_https(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value.replace('http://', 'https://')
            elif isinstance(value, (dict, list)):
                replace_http_with_https(value)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, str):
                data[index] = item.replace('http://', 'https://')
            elif isinstance(item, (dict, list)):
                replace_http_with_https(item)
    return data

def filter_quotes(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value.replace('"', '')
            elif isinstance(value, (dict, list)):
                filter_quotes(value)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, str):
                data[index] = item.replace('"', '')
            elif isinstance(item, (dict, list)):
                filter_quotes(item)
    return data

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['result_count'] = 6  # 初始化搜索结果数量
        return redirect(url_for('search_results', song_name=request.form['song_name']))
    return render_template('index.html')

@app.route('/results', methods=['GET', 'POST'])
def search_results():
    if request.method == 'POST':
        song_name = request.form['song_name']
        session['result_count'] = 6  # 重新初始化搜索结果数量
        return redirect(url_for('search_results', song_name=song_name))
    
    song_name = request.args.get('song_name', '')
    result_count = session.get('result_count', 6)  # 获取动态的结果数量
    list_search = QQM.search_music(song_name, result_count) if song_name else []
    
    results = []
    for i in range(min(result_count, len(list_search))):  # 避免下标越界错误
        song = list_search[i]
        try:
            songmid = song['songmid']
            albummid = song.get('albummid', '')
            songname = song['songname'].replace('"', '')
            singer = song['singer'][0]['name'].replace('"', '')
            albumname = song['albumname']
            duration = song['interval']  # 获取时长（单位为秒）
            
            # 转换时长格式
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            music_url = QQM.get_music_url(songmid)
            img_url = f'https://y.qq.com/music/photo_new/T002R800x800M000{albummid}.jpg?max_age=2592000' if albummid else 'https://axidiqolol53.objectstorage.ap-seoul-1.oci.customer-oci.com/n/axidiqolol53/b/lusic/o/resources/cover.jpg'
            
            results.append({
                'songname': songname,
                'singer': singer,
                'albumname': albumname,
                'duration': duration_str,
                'music_url': music_url,
                'img_url': img_url,
                'songmid': songmid
            })
        except (KeyError, IndexError):
            continue
    
    session['results'] = results  # 存储搜索结果到会话
    results = replace_http_with_https(results)  # 确保返回的数据中将 HTTP 替换为 HTTPS
    return render_template('index.html', results=results, song_name=song_name)

@app.route('/load_more', methods=['POST'])
def load_more():
    if 'result_count' not in session:
        return jsonify({"error": "Session expired"}), 400

    try:
        data = request.get_json()
        song_name = data.get('song_name', '')
    except Exception as e:
        return jsonify({"error": "Invalid input"}), 400

    session['result_count'] += 6  # 增加结果数量
    total_result_count = session.get('result_count', 6)
    list_search = QQM.search_music(song_name, total_result_count) if song_name else []
    
    new_results = []
    for i in range(total_result_count - 6, min(total_result_count, len(list_search))):  # 避免下标越界错误
        song = list_search[i]
        try:
            songmid = song['songmid']
            albummid = song.get('albummid', '')
            songname = song['songname'].replace('"', '')
            singer = song['singer'][0]['name'].replace('"', '')
            albumname = song['albumname']
            duration = song['interval']  # 获取时长（单位为秒）
            
            # 转换时长格式
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            music_url = QQM.get_music_url(songmid)
            img_url = f'https://y.qq.com/music/photo_new/T002R800x800M000{albummid}.jpg?max_age=2592000' if albummid else 'https://axidiqolol53.objectstorage.ap-seoul-1.oci.customer-oci.com/n/axidiqolol53/b/lusic/o/resources/cover.jpg'
            
            new_results.append({
                'songname': songname,
                'singer': singer,
                'albumname': albumname,
                'duration': duration_str,
                'music_url': music_url,
                'img_url': img_url,
                'songmid': songmid
            })
        except (KeyError, IndexError):
            continue

    new_results = replace_http_with_https(new_results)  # 确保返回的数据中将 HTTP 替换为 HTTPS
    return jsonify(new_results)

@app.route('/info/<songmid>', methods=['GET'])
def info(songmid):
    search_term = request.args.get('search_term')
    info = get_music_info(songmid, search_term)
    if info:
        info = replace_http_with_https(info)  # 确保返回的数据中将 HTTP 替换为 HTTPS
        info = filter_quotes(info)  # 确保返回的数据中移除双引号
        return jsonify(info)
    else:
        return jsonify({"error": "No matching song found"}), 404

@app.route('/song', methods=['GET'])
def song():
    songmid = request.args.get('songmid')
    search_term = request.args.get('search_term')
    if songmid and search_term:
        info = get_music_info(songmid, search_term)
        if info:
            info = replace_http_with_https(info)  # 确保返回的数据中将 HTTP 替换为 HTTPS
            info = filter_quotes(info)  # 确保返回的数据中移除双引号
            return render_template('song.html', **info)
        else:
            return "No matching song found", 404
    else:
        return "Missing songmid or search_term", 400

def get_music_info(songmid, search_term):
    result_count = session.get('result_count', 6)
    search_result = QQM.search_music(search_term, result_count)

    for song in search_result:
        try:
            if song['songmid'] == songmid:
                songname = song['songname'].replace('"', '')
                singer = song['singer'][0]['name'].replace('"', '')
                albumname = song['albumname']
                duration = song['interval']
                albummid = song.get('albummid', '')

                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"

                try:
                    lyrics = QQM.get_lyrics(songmid)
                    # 过滤歌词中的异常
                    lyrics = lyrics.replace("&apos;", "'")
                except KeyError:
                    lyrics = '无歌词信息'
                except AttributeError:
                    lyrics = '无法获取歌词'

                music_url = QQM.get_music_url(songmid)
                img_url = f'https://y.qq.com/music/photo_new/T002R800x800M000{albummid}.jpg?max_age=2592000' if albummid else 'https://axidiqolol53.objectstorage.ap-seoul-1.oci.customer-oci.com/n/axidiqolol53/b/lusic/o/resources/cover.jpg'

                return {
                    "songname": songname,
                    "singer": singer,
                    "albumname": albumname,
                    "duration": duration_str,
                    "songmid": songmid,
                    "lyrics": lyrics,
                    "img_url": img_url,
                    "music_url": music_url
                }
        except (KeyError, IndexError):
            continue

    return None

@app.route('/qualities', methods=['GET'])
def get_qualities():
    songmid = request.args.get('songmid')
    if not songmid:
        return jsonify({"error": "songmid parameter is required"}), 400

    qqmusic = QQMusic()
    qqmusic.set_cookies(cookie_str)

    # 音质类型列表，从高到低依次尝试
    file_types = ['flac', '320', '128', 'm4a']
    results = {}

    for file_type in file_types:
        result = qqmusic.get_music_url(songmid, file_type)
        if result:
            results[file_type] = result
        time.sleep(0.1)

    # 确定最高可用音质类型
    highest_quality = next((ft for ft in file_types if ft in results), None)

    # 构造 JSON 输出
    output = {
        'available_qualities': list(results.keys()),
        'urls': results,
        'highest_quality': highest_quality
    }

    return jsonify(output)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3101)
