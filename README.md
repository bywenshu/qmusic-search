## 声明：
本项目不提供 QQ 音乐会员歌曲破解服务。要听 VIP 歌曲请自己开通会员。  
本项目仅供个人使用，不得公用。请尊重版权，不得利用本项目的任何功能传播盗版资源。  
本人第一次开源自己的作品，所以还存在非常多不成熟的地方，请见谅。详细部署方式已经以视频方式附上。  

## 准备工作：
一个域名（添加两个解析，分别为 `[主域名]` 和 `[API 域名]` 添加解析）；  
一台服务器；  
S3 对象存储服务；  
良好的网络；  
基础的 Linux 云服务器操作知识。

## 部分文件功能介绍：
`app.py` 网站后端、搜索功能。  
`metadata.py` 嵌入歌曲的歌词和封面等元信息并规范文件名，然后上传到 S3 存储。  
`index.html` 网站前端。  
`song.html` 音乐播放页面，可调用 `metadata.py` 以获取音乐。

## 项目预览：
[项目预览视频（存储在 Cloudflare R2）](https://pub-2f343bc3f5884c2bb9d409ccde31c5af.r2.dev/qmusic-search.mp4)

## 部署教程视频：
### YouTube
[![Watch the video](https://pub-2f343bc3f5884c2bb9d409ccde31c5af.r2.dev/cover.jpg)](https://www.youtube.com/watch?v=e4fQuX6Dizo)
### bilibili
[部署教程](https://www.bilibili.com/video/BV1AnhDenE7G)
### Cloudflare R2
[部署教程](https://pub-2f343bc3f5884c2bb9d409ccde31c5af.r2.dev/qmusic-search-Deployment.mp4)

## 环境配置：
我开发用的环境：`Python 3.10.12`
其它比较新 Python 环境应该也是可用的，但未测试。
部分资源使用 Cloudflare R2 存储，故可能无法在中国大陆加载，请搜索 `r2.dev` 并替换。

## 安装库：
```sh
pip3 install -r requirements.txt
```

## 获取 QQ 音乐 Cookies：
在 QQ 音乐电脑版官网登录账号后，浏览器控制台输入 `document.cookie` 即可获取 Cookies。

## 必须配置：
### Cookies 填写位置：
```python
app.py          line 13
```

### CORS 设置：
```python
metadata.py     line 18
```
说明：这里要允许 `[主域名]` 的访问，故填入 `[主域名]` 或通配符都可（见下文）。

### S3 存储桶配置：
```python
metadata.py     line 24 ~ 27
metadata.py     line 192 ~ 197
```

### /processSong 函数调用地址：
```html
song.html       line 330
```
说明：/processSong 路由调用 `metadata.py` 中的嵌入元信息功能。这里要填入 `[API 域名]`（见下文）。

## 可选项：
### 前端网页标题：
```html
index.html      line 5
```

### 网站首页公告：
```html
index.html      line 178 ~ 188
```

### 浏览器 Logo：
```html
index.html      line 7
song.html       line 7
```

### 特定歌曲直接返回一个可设定的链接，不对其进行处理：
```python
metadata.py     line 150
```

### 少部分歌曲没有封面图，可个性化设置默认封面图：
```python
app.py          line 15
song.html       line 210
```

### API 返回信息中，一些歌词因含特殊符号而显示异常，需要替换才能保证嵌入歌词显示正常：
```python
metadata.py          line 145
```
说明：代码中已经包括了对 `&apos;` 和 `&quot;` 的替换，分别替换为了 `英文单引号` 和 `英文双引号`。前端无此问题。

## 部署
### 参照上文准备 Python 环境。
### 运行 app.py 和 metadata.py
```python
python3 app.py
```
```python
python3 metadata.py
```
### 域名配置
`[主域名]` `反向代理` 本机的 `3101` 端口；
`[API 域名]` `反向代理` 本机的 `3201` 端口。

## 鸣谢：
本项目的诞生离不开以下项目：  
https://github.com/MCQTSS/MCQTSS_QQMusic  
https://github.com/listen1/listen1_chrome_extension/blob/master/js/provider/qq.js
