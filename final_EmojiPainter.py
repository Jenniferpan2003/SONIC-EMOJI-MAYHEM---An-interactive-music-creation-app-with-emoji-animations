#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Music Emoji Painter - Interactive Music Creation Game
Created: 2025-10-23
Description: A pygame-based interactive music creation tool where users press keys 1-7 
             to create visual/audio compositions using emoji images.
"""

import pygame
import random
import sys
import os
import datetime
from collections import Counter
import numpy as np
import cv2
try:
    from moviepy.editor import VideoClip, AudioClip
except ImportError:
    from moviepy.video.VideoClip import VideoClip
    from moviepy.audio.AudioClip import AudioClip
import tempfile

# 初始化pygame
pygame.init()

# 设置
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🎵 Music Emoji Painter 🎨")

# 颜色定义
BACKGROUND = (255, 250, 245)  # 淡米色背景
CANVAS_BG = (240, 248, 255)   # 淡蓝色画布
TEXT_COLOR = (75, 0, 130)     # 深紫色文字
BUTTON_COLOR = (70, 130, 180)  # 钢蓝色按钮

# 获取当前脚本目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_images():
    """加载0.png到9.png图片文件"""
    images = {}
    for i in range(0, 10):  # 0-9对应10个音符
        try:
            img_path = os.path.join(SCRIPT_DIR, f"{i}.png")
            if os.path.exists(img_path):
                img = pygame.image.load(img_path)
                # 缩放图片到合适大小
                img = pygame.transform.scale(img, (50, 50))
                images[i] = img
            else:
                print(f"Image {i}.png not found, will use None")
                images[i] = None
        except pygame.error as e:
            print(f"Cannot load image {i}.png: {e}")
            images[i] = None
    return images

# 加载所有图片
fruit_images = load_images()

# 音符到emoji的映射（0-9键）
note_fruits = {
    pygame.K_0: {"name": "0", "image": fruit_images[0], "color": (255, 192, 203), "pitch": "0", "sound_index": 0},
    pygame.K_1: {"name": "1", "image": fruit_images[1], "color": (144, 238, 144), "pitch": "1", "sound_index": 1},
    pygame.K_2: {"name": "2", "image": fruit_images[2], "color": (255, 99, 71), "pitch": "2", "sound_index": 2},
    pygame.K_3: {"name": "3", "image": fruit_images[3], "color": (255, 165, 0), "pitch": "3", "sound_index": 3},
    pygame.K_4: {"name": "4", "image": fruit_images[4], "color": (255, 255, 0), "pitch": "4", "sound_index": 4},
    pygame.K_5: {"name": "5", "image": fruit_images[5], "color": (147, 112, 219), "pitch": "5", "sound_index": 5},
    pygame.K_6: {"name": "6", "image": fruit_images[6], "color": (255, 20, 147), "pitch": "6", "sound_index": 6},
    pygame.K_7: {"name": "7", "image": fruit_images[7], "color": (70, 130, 180), "pitch": "7", "sound_index": 7},
    pygame.K_8: {"name": "8", "image": fruit_images[8], "color": (100, 149, 237), "pitch": "8", "sound_index": 8},
    pygame.K_9: {"name": "9", "image": fruit_images[9], "color": (218, 112, 214), "pitch": "9", "sound_index": 9},
}

def generate_tone(frequency=440, duration=500, wave_type='sine'):
    """生成指定频率和时长的音调"""
    sample_rate = 44100
    n_samples = int(sample_rate * duration / 1000.0)
    
    # 创建立体声数组
    arr = np.zeros((n_samples, 2), dtype=np.int16)
    for i in range(n_samples):
        t = float(i) / sample_rate
        if wave_type == 'sine':
            # 添加淡入淡出效果以减少噪音
            envelope = 1.0
            if i < n_samples * 0.1:  # 淡入
                envelope = i / (n_samples * 0.1)
            elif i > n_samples * 0.9:  # 淡出
                envelope = (n_samples - i) / (n_samples * 0.1)
            
            sample_value = int(32767.0 * 0.3 * envelope * np.sin(2 * np.pi * frequency * t))
            arr[i][0] = sample_value  # 左声道
            arr[i][1] = sample_value  # 右声道
    
    return pygame.sndarray.make_sound(arr)

# 加载音效 - 从music文件夹加载000-009音频文件
sounds = []
music_folder = os.path.join(SCRIPT_DIR, "music")
for i in range(10):  # 0-9
    sound_loaded = False
    # 尝试加载.wav和.mp3格式
    for ext in ['.wav', '.mp3']:
        sound_path = os.path.join(music_folder, f"{i:03d}{ext}")
        if os.path.exists(sound_path):
            try:
                sounds.append(pygame.mixer.Sound(sound_path))
                print(f"Loaded sound: {i:03d}{ext}")
                sound_loaded = True
                break
            except Exception as e:
                print(f"Error loading {i:03d}{ext}: {e}")
    
    # 如果没有加载成功，使用生成的音调作为后备
    if not sound_loaded:
        frequencies = [262, 294, 330, 349, 392, 440, 494, 523, 587, 659]  # 10个音符
        print(f"Using generated tone for sound {i}")
        sounds.append(generate_tone(frequencies[i], 800))

class GameState:
    """游戏状态管理类"""
    def __init__(self):
        self.played_fruits = []  # 记录弹奏的emoji序列
        self.song_name = ""  # 作品名（初始为空，必须填写）
        self.audio_data = []  # 记录音频数据用于回放
        self.editing_name = True  # 初始进入编辑模式
        self.name_input = ""  # 当前输入的文字
        self.download_button_rect = None  # 下载按钮的矩形区域
        self.save_message = ""  # 保存成功的消息
        self.save_message_timer = 0  # 消息显示计时器
        self.save_success = True  # 保存是否成功
        self.right_emojis_to_show = []  # 右侧要显示的emoji列表（按出现顺序）
        self.right_emoji_animation_times = []  # 每个emoji的动画开始时间
        self.cursor_position = 0  # 光标位置
        self.selection_start = 0  # 选择起始位置
        self.selection_end = 0  # 选择结束位置
        self.placed_positions = []  # 记录已放置的emoji位置和大小
        self.recording_video = False  # 录制状态（输入名称后第一次按键开始录制）
        self.video_frames = []  # 存储视频帧
        self.frame_timestamps = []  # 存储每帧的时间戳
        self.recording_start_time = None  # 录制开始时间
        self.audio_events = []  # 存储音频事件 (时间戳, 音频索引)
        self.name_entered = False  # 是否已输入作品名
        self.on_start_page = True  # 是否在开始页面
        self.start_button_rect = None  # Start按钮的矩形区域
        self.back_arrow_rect = None  # 返回箭头的矩形区域
        self.popup_animation_start = 0  # 弹窗动画开始时间

game_state = GameState()

# 字体设置 - 使用自定义字体（相对路径）
ENGLISH_FONT_PATH = os.path.join(SCRIPT_DIR, "led_counter-7.ttf")
CHINESE_FONT_PATH = os.path.join(SCRIPT_DIR, "SourceHanSansCN-Bold.otf")

# 英文字体（LED样式）
try:
    title_font_en = pygame.font.Font(ENGLISH_FONT_PATH, 68)
    font_en = pygame.font.Font(ENGLISH_FONT_PATH, 32)
    small_font_en = pygame.font.Font(ENGLISH_FONT_PATH, 19)  # 24 - 5 = 19
    path_font_en = pygame.font.Font(ENGLISH_FONT_PATH, 18)
    english_font_loaded = True
except:
    print("English font not found, using system font")
    title_font_en = pygame.font.SysFont('arial', 68, bold=True)
    font_en = pygame.font.SysFont('arial', 32)
    small_font_en = pygame.font.SysFont('arial', 19)  # 24 - 5 = 19
    path_font_en = pygame.font.SysFont('arial', 18)
    english_font_loaded = False

# 中文字体（思源黑体）
try:
    title_font_cn = pygame.font.Font(CHINESE_FONT_PATH, 68)
    font_cn = pygame.font.Font(CHINESE_FONT_PATH, 32)
    small_font_cn = pygame.font.Font(CHINESE_FONT_PATH, 19)  # 24 - 5 = 19
    path_font_cn = pygame.font.Font(CHINESE_FONT_PATH, 18)
    chinese_font_loaded = True
except:
    print("Chinese font not found, using system font")
    title_font_cn = pygame.font.SysFont('microsoftyahei', 68, bold=True)
    font_cn = pygame.font.SysFont('microsoftyahei', 32)
    small_font_cn = pygame.font.SysFont('microsoftyahei', 19)  # 24 - 5 = 19
    path_font_cn = pygame.font.SysFont('microsoftyahei', 18)
    chinese_font_loaded = False

# 默认使用英文字体（向后兼容）
title_font = title_font_en
font = font_en
small_font = small_font_en
path_font = path_font_en

def render_mixed_text(text, font_en, font_cn, color):
    """
    渲染混合中英文文本
    英文使用LED字体，中文使用思源黑体
    """
    if not text:
        return pygame.Surface((0, 0))
    
    # 检测文本是否包含中文
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
    
    if has_chinese:
        # 包含中文，使用中文字体
        return font_cn.render(text, True, color)
    else:
        # 纯英文，使用英文字体
        return font_en.render(text, True, color)

def draw_big_fruit_effect(fruit_data):
    """绘制大图片特效"""
    if game_state.big_fruit_effect:
        alpha = max(0, 255 - (pygame.time.get_ticks() - game_state.big_fruit_timer) * 255 // 500)
        if alpha > 0:
            # 绘制半透明背景
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            s.fill((255, 255, 255, alpha // 3))
            screen.blit(s, (0, 0))
            
            # 绘制巨大emoji图片
            if fruit_data["image"]:
                big_image = pygame.transform.scale(fruit_data["image"], (250, 250))
                image_rect = big_image.get_rect(center=(WIDTH//2, HEIGHT//2 + 20))
                screen.blit(big_image, image_rect)
            else:
                # 如果图片加载失败，显示文字
                fruit_text = title_font.render(fruit_data["name"], True, fruit_data["color"])
                text_rect = fruit_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 20))
                screen.blit(fruit_text, text_rect)

def draw_canvas():
    """绘制emoji画布"""
    # 不再绘制左侧画布的背景和边框，只显示最多弹奏的emoji
    # canvas_rect = pygame.Rect(80, 210, 470, 400)  # 左侧画布位置
    # pygame.draw.rect(screen, CANVAS_BG, canvas_rect, border_radius=10)
    # pygame.draw.rect(screen, (100, 100, 100), canvas_rect, 3, border_radius=10)
    
    # 绘制左侧标题 "Emoji Personality"
    label_text = font_en.render("Emoji Personality", True, TEXT_COLOR)
    label_x = 80 + 235 - label_text.get_width() // 2  # 居中：80 + 470/2
    label_y = 210 - 50  # 在框上方50像素（向上移动5像素）
    screen.blit(label_text, (label_x, label_y))
    
    if not game_state.played_fruits:
        return
    
    # 统计emoji数量，找到弹奏最多的
    fruit_counts = Counter([fruit["name"] for fruit in game_state.played_fruits])
    most_common_name, most_common_count = fruit_counts.most_common(1)[0]
    
    # 找到对应的emoji数据
    fruit_data = next(f for f in note_fruits.values() if f["name"] == most_common_name)
    
    # 在左侧框中央显示最多的emoji
    if fruit_data["image"]:
        # 显示大图片，完全居中
        big_image = pygame.transform.scale(fruit_data["image"], (360, 360))
        image_x = 80 + 235 - 180  # 居中：80 + 470/2 - 360/2
        image_y = 210 + 200 - 180  # 居中：210 + 400/2 - 360/2
        screen.blit(big_image, (image_x, image_y))

def draw_statistics():
    """绘制统计信息"""
    # 绘制右侧标题 "Emoji Music Artwork"
    label_text = font_en.render("Emoji Music Artwork", True, TEXT_COLOR)
    label_x = 640 + 250 - label_text.get_width() // 2  # 居中：640 + 500/2
    label_y = 210 - 50  # 在框上方50像素
    screen.blit(label_text, (label_x, label_y))
    
    stats_rect = pygame.Rect(640, 210, 500, 400)  # 右侧统计框位置
    pygame.draw.rect(screen, BACKGROUND, stats_rect, border_radius=10)
    pygame.draw.rect(screen, (100, 100, 100), stats_rect, 3, border_radius=10)
    
    if not game_state.right_emojis_to_show:
        return
    
    current_time = pygame.time.get_ticks()
    animation_duration = 300  # 每个emoji动画持续300毫秒
    
    for fruit_data in game_state.right_emojis_to_show:
        # 使用预先生成的随机位置、大小和角度
        target_x = fruit_data["random_x"]
        target_y = fruit_data["random_y"]
        target_size = fruit_data["random_display_size"]
        rotation_angle = fruit_data["random_angle"]
        
        # 计算这个emoji的动画进度（使用自己的animation_start时间）
        emoji_animation_start = fruit_data["animation_start"]
        elapsed = current_time - emoji_animation_start
        
        if elapsed < animation_duration:
            # 动画进行中，使用缓动函数
            progress = elapsed / animation_duration
            # 使用ease-out效果：开始快，结束慢
            progress = 1 - (1 - progress) ** 3
            current_size = int(target_size * progress)
        else:
            # 动画完成
            current_size = target_size
        
        if current_size > 0 and fruit_data["image"]:
            # 缩放emoji到当前大小
            emoji_image = pygame.transform.scale(fruit_data["image"], (current_size, current_size))
            
            # 旋转emoji
            rotated_image = pygame.transform.rotate(emoji_image, rotation_angle)
            
            # 获取旋转后的rect并居中
            rotated_rect = rotated_image.get_rect(center=(target_x + target_size // 2, target_y + target_size // 2))
            
            # 绘制emoji
            screen.blit(rotated_image, rotated_rect)

def draw_back_arrow():
    """绘制返回箭头（左上角）"""
    arrow_size = 40
    arrow_x = 30
    arrow_y = 63  # 与作品名称边框上边缘对齐
    
    # 检查鼠标是否悬停在箭头上
    mouse_pos = pygame.mouse.get_pos()
    arrow_rect = pygame.Rect(arrow_x - 10, arrow_y - 10, arrow_size + 20, arrow_size + 20)
    is_hovering = arrow_rect.collidepoint(mouse_pos)
    
    # 根据悬停状态选择颜色
    arrow_color = (65, 105, 225) if is_hovering else (0, 0, 0)  # 皇家蓝或黑色
    
    # 绘制向左的箭头（三角形 + 矩形）
    # 箭头头部（三角形）
    arrow_head = [
        (arrow_x, arrow_y + arrow_size // 2),  # 左尖端
        (arrow_x + arrow_size // 2, arrow_y),  # 上顶点
        (arrow_x + arrow_size // 2, arrow_y + arrow_size)  # 下顶点
    ]
    pygame.draw.polygon(screen, arrow_color, arrow_head)
    
    # 箭头尾部（矩形）
    tail_rect = pygame.Rect(arrow_x + arrow_size // 2 - 5, arrow_y + arrow_size // 3, arrow_size // 2, arrow_size // 3)
    pygame.draw.rect(screen, arrow_color, tail_rect)
    
    # 保存箭头区域供点击检测
    game_state.back_arrow_rect = arrow_rect
    
    return arrow_rect

def draw_start_page():
    """绘制开始页面"""
    # 绘制背景
    screen.fill(BACKGROUND)
    
    # 绘制主标题（居中，上方）
    title = title_font.render("Music Emoji Painter", True, TEXT_COLOR)
    title_y = 160
    screen.blit(title, (WIDTH//2 - title.get_width()//2, title_y))
    
    # 绘制作品名称输入框（居中）
    name_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 - 70, 400, 50)
    
    # 根据是否正在编辑改变背景色
    if game_state.editing_name:
        pygame.draw.rect(screen, (255, 255, 200), name_rect, border_radius=10)  # 黄色背景表示正在编辑
        pygame.draw.rect(screen, (255, 165, 0), name_rect, 3, border_radius=10)  # 橙色边框
    else:
        pygame.draw.rect(screen, (255, 255, 255), name_rect, border_radius=10)  # 白色背景
        pygame.draw.rect(screen, TEXT_COLOR, name_rect, 2, border_radius=10)  # 普通边框
    
    # 显示当前文字
    display_text = game_state.name_input if game_state.editing_name else game_state.song_name
    
    # 绘制文字（居中）
    if display_text:
        name_text = render_mixed_text(display_text, font_en, font_cn, TEXT_COLOR)
        text_x = name_rect.centerx - name_text.get_width() // 2
        text_y = name_rect.y + 10
    else:
        # 如果没有文字，显示提示
        name_text = font_en.render("Enter your work name...", True, (150, 150, 150))
        text_x = name_rect.centerx - name_text.get_width() // 2
        text_y = name_rect.y + 10
    
    # 如果正在编辑，绘制光标
    if game_state.editing_name and display_text:
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in display_text)
        active_font = font_cn if has_chinese else font_en
        
        # 绘制光标
        cursor_visible = (pygame.time.get_ticks() // 500) % 2
        if cursor_visible and game_state.selection_start == game_state.selection_end:
            cursor_text = display_text[:game_state.cursor_position]
            cursor_x = text_x + active_font.render(cursor_text, True, TEXT_COLOR).get_width()
            pygame.draw.line(screen, TEXT_COLOR, (cursor_x, text_y), (cursor_x, text_y + name_text.get_height()), 2)
    
    # 绘制文字
    screen.blit(name_text, (text_x, text_y))
    
    # 提示文字（居中，输入框上方）
    try:
        prompt_font = pygame.font.Font(ENGLISH_FONT_PATH, 24)
    except:
        prompt_font = pygame.font.SysFont('arial', 24)
    
    if game_state.editing_name:
        prompt_text = prompt_font.render("Type your work name (Press Enter to confirm)", True, (255, 100, 0))
    else:
        prompt_text = prompt_font.render("Click the box to enter your work name", True, TEXT_COLOR)
    
    prompt_x = WIDTH//2 - prompt_text.get_width() // 2
    screen.blit(prompt_text, (prompt_x, name_rect.y - 40))
    
    # 绘制Start按钮（居中，输入框下方）
    button_width = 200
    button_height = 60
    button_x = WIDTH//2 - button_width//2
    button_y = HEIGHT//2 + 50
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
    
    # 检查鼠标是否悬停在按钮上
    mouse_pos = pygame.mouse.get_pos()
    is_hovering = button_rect.collidepoint(mouse_pos)
    
    # 检查是否可以点击（已输入名称）
    can_start = len(game_state.song_name.strip()) > 0
    
    if can_start:
        if is_hovering:
            button_color = (255, 130, 130)  # 悬停时稍微亮一点
        else:
            button_color = (255, 106, 106)  # 成功按钮的颜色
    else:
        button_color = (200, 200, 200)  # 灰色表示不可用
    
    pygame.draw.rect(screen, button_color, button_rect, border_radius=10)
    pygame.draw.rect(screen, (100, 100, 100), button_rect, 3, border_radius=10)
    
    # 绘制按钮文字
    button_text = font_en.render("START", True, (255, 255, 255))
    button_text_x = button_rect.centerx - button_text.get_width() // 2
    button_text_y = button_rect.centery - button_text.get_height() // 2
    screen.blit(button_text, (button_text_x, button_text_y))
    
    # 绘制作者信息（右下角）
    try:
        author_font = pygame.font.Font(ENGLISH_FONT_PATH, 18)
    except:
        author_font = pygame.font.SysFont('arial', 18)
    
    author_info = [
        "Pan Jiani (Jennifer)",
        "MuddyTomato",
        "25126398G",
        "The Hong Kong Polytechnic University",
        "Innovation Multimedia Entertainment"
    ]
    
    author_y = HEIGHT - 120  # 从底部向上120像素开始
    for i, line in enumerate(author_info):
        author_text = author_font.render(line, True, (100, 100, 100))
        author_x = WIDTH - author_text.get_width() - 20  # 右边距20像素
        screen.blit(author_text, (author_x, author_y + i * 22))
    
    # 保存按钮rect供点击检测使用
    game_state.start_button_rect = button_rect
    
    return name_rect

def draw_controls():
    """绘制控制说明"""
    controls_y = 715
    controls_text = [
        "Press 0-9 to play emoji music. Press Space to finish then click Download&Save! Press R to restart."
    ]
    
    for i, text in enumerate(controls_text):
        control_text = small_font.render(text, True, (100, 100, 100))
        screen.blit(control_text, (WIDTH//2 - control_text.get_width()//2, controls_y + i * 30))

def draw_song_name_input():
    """绘制歌曲名称显示（只读，扩大一倍）"""
    # 扩大一倍：原来是400x40，现在是800x80
    name_rect = pygame.Rect(WIDTH//2 - 400, 63, 800, 80)
    
    # 只读模式：白色背景，紫色边框
    pygame.draw.rect(screen, (255, 255, 255), name_rect, border_radius=10)  # 白色背景
    pygame.draw.rect(screen, TEXT_COLOR, name_rect, 4, border_radius=10)  # 紫色边框（加粗到4px）
    
    # 显示作品名称
    display_text = game_state.song_name
    
    # 绘制文字（居中）- 使用更大的字体（64px，原来32px的两倍）
    try:
        large_font_en = pygame.font.Font(ENGLISH_FONT_PATH, 64)
        large_font_cn = pygame.font.Font(CHINESE_FONT_PATH, 64)
    except:
        large_font_en = pygame.font.SysFont('arial', 64)
        large_font_cn = pygame.font.SysFont('microsoftyahei', 64)
    
    name_text = render_mixed_text(display_text, large_font_en, large_font_cn, TEXT_COLOR)
    text_x = name_rect.centerx - name_text.get_width() // 2
    text_y = name_rect.centery - name_text.get_height() // 2
    
    # 绘制文字
    screen.blit(name_text, (text_x, text_y))
    
    # 提示文字已删除 - 第二页不显示提示
    
    return name_rect  # 返回矩形区域用于点击检测

def draw_save_message():
    """绘制保存消息弹窗（带动画效果）"""
    if game_state.save_message and pygame.time.get_ticks() - game_state.save_message_timer < 5000:  # 显示5秒
        # 计算动画进度（0-1）
        current_time = pygame.time.get_ticks()
        animation_duration = 300  # 动画持续300毫秒
        elapsed = current_time - game_state.popup_animation_start
        progress = min(1.0, elapsed / animation_duration)
        
        # 缓动函数 - 弹性效果
        if progress < 1.0:
            # 使用ease-out-back效果
            scale = progress * (1 + 0.3 * (1 - progress))
        else:
            scale = 1.0
        
        # 检查是否是简单的"请按空格键"消息
        is_simple_message = "Please press Space key to finish recording first!" in game_state.save_message
        
        # 计算弹窗位置和大小
        base_width = 800
        if is_simple_message:
            base_height = 120  # 扁平的框
        else:
            base_height = 200 if not game_state.save_success else 150
        
        popup_width = int(base_width * scale)
        popup_height = int(base_height * scale)
        popup_x = WIDTH//2 - popup_width//2
        popup_y = HEIGHT//2 - popup_height//2
        
        popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
        
        # 绘制半透明背景（渐显）
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay_alpha = int(128 * progress)
        overlay.fill((0, 0, 0, overlay_alpha))  # 半透明黑色
        screen.blit(overlay, (0, 0))
        
        # 根据成功或失败选择颜色
        if game_state.save_success:
            bg_color = (255, 106, 106)  # 红色背景 (成功)
            title_text = "Success!"
        else:
            bg_color = (112, 128, 144)  # SlateGrey (失败)
            title_text = "Failed!"
        
        # 绘制弹窗背景
        pygame.draw.rect(screen, bg_color, popup_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), popup_rect, 4, border_radius=10)  # 白色边框

        # 如果是简单消息，直接在中心显示文字，不显示标题
        if is_simple_message:
            # 直接在框的正中心显示消息（带缩放效果）
            message_surface_orig = font.render(game_state.save_message, True, (255, 255, 255))
            # 缩放文字
            scaled_width = int(message_surface_orig.get_width() * scale)
            scaled_height = int(message_surface_orig.get_height() * scale)
            message_surface = pygame.transform.scale(message_surface_orig, (scaled_width, scaled_height))
            message_rect = message_surface.get_rect(center=(popup_x + popup_width//2, popup_y + popup_height//2))
            screen.blit(message_surface, message_rect)
            return  # 早返回，不继续绘制其他内容
        
        # 绘制标题文字（非简单消息，带缩放效果）
        title_surface_orig = font.render(title_text, True, (255, 255, 255))
        # 缩放标题
        scaled_title_width = int(title_surface_orig.get_width() * scale)
        scaled_title_height = int(title_surface_orig.get_height() * scale)
        title_surface = pygame.transform.scale(title_surface_orig, (scaled_title_width, scaled_title_height))
        title_rect = title_surface.get_rect(center=(popup_x + popup_width//2, popup_y + int(35 * scale)))
        screen.blit(title_surface, title_rect)
        
        # 绘制保存路径信息（使用全局path_font）
        # 文字换行处理 - 先按\n分割，然后处理每行
        max_width = popup_width - 40  # 留出边距
        raw_lines = game_state.save_message.split('\n')
        lines = []
        
        for raw_line in raw_lines:
            # 每一行再按空格分割，处理长行
            words = raw_line.split(' ')
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_surface = path_font.render(test_line, True, (255, 255, 255))
                if test_surface.get_width() <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
        
        # 绘制每行文字（带缩放效果）
        line_height = int(22 * scale)
        start_y = popup_y + int(70 * scale)
        for i, line in enumerate(lines):
            line_text_orig = path_font.render(line, True, (255, 255, 255))
            # 缩放文字
            scaled_line_width = int(line_text_orig.get_width() * scale)
            scaled_line_height = int(line_text_orig.get_height() * scale)
            line_text = pygame.transform.scale(line_text_orig, (scaled_line_width, scaled_line_height))
            line_rect = line_text.get_rect(center=(popup_x + popup_width//2, start_y + i * line_height))
            screen.blit(line_text, line_rect)
        
        # 绘制关闭提示（带缩放效果）
        close_text_orig = small_font.render("(Click anywhere to close)", True, (200, 200, 200))
        scaled_close_width = int(close_text_orig.get_width() * scale)
        scaled_close_height = int(close_text_orig.get_height() * scale)
        close_text = pygame.transform.scale(close_text_orig, (scaled_close_width, scaled_close_height))
        close_rect = close_text.get_rect(center=(popup_x + popup_width//2, popup_y + popup_height - int(25 * scale)))
        screen.blit(close_text, close_rect)

def draw_download_button():
    """绘制下载保存按钮"""
    button_width = 350
    button_height = 60
    button_x = WIDTH//2 - button_width//2
    button_y = 630  # 在控制说明上方
    
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
    
    # 检查鼠标是否悬浮在按钮上
    mouse_pos = pygame.mouse.get_pos()
    is_hovering = button_rect.collidepoint(mouse_pos)
    
    # 如果悬浮，放大按钮
    if is_hovering:
        scale_factor = 1.1  # 放大10%
        hover_width = int(button_width * scale_factor)
        hover_height = int(button_height * scale_factor)
        hover_x = WIDTH//2 - hover_width//2
        hover_y = button_y - (hover_height - button_height)//2  # 居中放大
        hover_rect = pygame.Rect(hover_x, hover_y, hover_width, hover_height)
        
        # 绘制放大的按钮
        pygame.draw.rect(screen, BUTTON_COLOR, hover_rect, border_radius=10)  # 蓝色背景
        pygame.draw.rect(screen, (100, 100, 100), hover_rect, 3, border_radius=10)  # 灰色边框
        
        # 绘制放大的文字 - 使用自定义字体
        try:
            hover_font = pygame.font.Font(ENGLISH_FONT_PATH, int(32 * scale_factor))
        except:
            hover_font = pygame.font.SysFont('arial', int(32 * scale_factor))
        download_text = hover_font.render("Download & Save", True, (255, 255, 255))
        text_rect = download_text.get_rect(center=hover_rect.center)
        screen.blit(download_text, text_rect)
        
        return button_rect  # 仍然返回原始按钮区域用于点击检测
    else:
        # 正常状态的按钮
        pygame.draw.rect(screen, BUTTON_COLOR, button_rect, border_radius=10)  # 蓝色背景
        pygame.draw.rect(screen, (100, 100, 100), button_rect, 3, border_radius=10)  # 灰色边框
        
        # 绘制按钮文字
        try:
            button_font = pygame.font.Font(ENGLISH_FONT_PATH, 32)
        except:
            button_font = pygame.font.SysFont('arial', 32)
        download_text = button_font.render("Download & Save", True, (255, 255, 255))
        text_rect = download_text.get_rect(center=button_rect.center)
        screen.blit(download_text, text_rect)
        
        return button_rect  # 返回按钮区域用于点击检测

def generate_audio_track(duration, audio_events, sample_rate=44100):
    """生成音频轨道 - 使用实际加载的音频文件"""
    # 创建空的音频数组（双声道）
    num_samples = int(duration * sample_rate)
    audio_samples = np.zeros((num_samples, 2), dtype=np.float32)
    
    for timestamp, sound_index in audio_events:
        # 确保sound_index在有效范围内
        if sound_index < 0 or sound_index >= len(sounds):
            continue
        
        # 获取对应的音频
        sound = sounds[sound_index]
        
        # 将pygame.mixer.Sound转换为numpy数组
        sound_array = pygame.sndarray.array(sound)
        
        # 确保是2D数组（立体声）
        if len(sound_array.shape) == 1:
            # 单声道，转为立体声
            sound_array = np.column_stack((sound_array, sound_array))
        
        # 转换为float32 (-1.0 to 1.0)
        if sound_array.dtype == np.int16:
            sound_array = sound_array.astype(np.float32) / 32768.0
        
        # 计算插入位置
        start_sample = int(timestamp * sample_rate)
        sound_length = len(sound_array)
        end_sample = min(start_sample + sound_length, num_samples)
        
        # 添加到音频轨道
        if start_sample < num_samples:
            actual_length = end_sample - start_sample
            audio_samples[start_sample:end_sample] += sound_array[:actual_length]
    
    # 归一化防止削波
    max_val = np.abs(audio_samples).max()
    if max_val > 1.0:
        audio_samples = audio_samples / max_val
    
    return audio_samples

def save_work():
    """保存包含音频的视频"""
    if not game_state.video_frames:
        print("No frames to save!")
        return False, "No recording available"
    
    # 创建保存目录（使用绝对路径）
    save_dir = os.path.join(SCRIPT_DIR, "saved_works")
    print(f"📁 Save directory: {save_dir}")
    
    # 确保目录存在
    try:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            print(f"✅ Created directory: {save_dir}")
        else:
            print(f"✅ Directory exists: {save_dir}")
    except Exception as e:
        print(f"❌ Error creating directory: {e}")
        return False, f"Failed to create directory: {e}"
    
    # 生成文件名（使用当前时间）
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 清理文件名中的非法字符
    safe_song_name = "".join(c for c in game_state.song_name if c.isalnum() or c in (' ', '-', '_', '中', '文')).strip()
    if not safe_song_name:
        safe_song_name = "music_emoji"
    filename = f"{safe_song_name}_{timestamp}"
    video_path = os.path.join(save_dir, f"{filename}.mp4")
    print(f"💾 Target file: {video_path}")
    
    try:
        print(f"🎬 Saving video with {len(game_state.video_frames)} frames and {len(game_state.audio_events)} audio events...")
        
        fps = 60
        duration = len(game_state.video_frames) / fps
        
        # 创建视频函数
        def make_frame(t):
            frame_index = int(t * fps)
            if frame_index >= len(game_state.video_frames):
                frame_index = len(game_state.video_frames) - 1
            # OpenCV使用BGR，moviepy使用RGB
            frame = game_state.video_frames[frame_index]
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 创建视频clip
        video_clip = VideoClip(make_frame, duration=duration)
        
        # 生成音频
        if game_state.audio_events:
            print("🎵 Generating audio track...")
            audio_array = generate_audio_track(duration, game_state.audio_events)
            
            def make_audio_frame(t):
                # t 可能是数组，需要处理
                if isinstance(t, np.ndarray):
                    # 如果是数组，返回对应的音频片段
                    start_idx = int(t[0] * 44100)
                    end_idx = int(t[-1] * 44100) + 1
                    end_idx = min(end_idx, len(audio_array))
                    if start_idx >= len(audio_array):
                        return np.zeros((len(t), 2), dtype=np.float32)
                    result = audio_array[start_idx:end_idx]
                    # 确保返回正确的长度
                    if len(result) < len(t):
                        padding = np.zeros((len(t) - len(result), 2), dtype=np.float32)
                        result = np.vstack([result, padding])
                    return result[:len(t)]
                else:
                    # 如果是单个值
                    sample_index = int(t * 44100)
                    if sample_index >= len(audio_array):
                        return np.zeros(2, dtype=np.float32)
                    return audio_array[sample_index]
            
            audio_clip = AudioClip(make_audio_frame, duration=duration, fps=44100)
            video_clip = video_clip.with_audio(audio_clip)
        
        # 写入视频文件
        print("💾 Writing video file...")
        video_clip.write_videofile(
            video_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=tempfile.mktemp(suffix='.m4a'),
            remove_temp=True
        )
        
        # 保存音乐数据
        with open(os.path.join(save_dir, f"{filename}_music.txt"), "w", encoding="utf-8") as f:
            f.write(f"Song Name: {game_state.song_name}\n")
            f.write(f"Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Frames: {len(game_state.video_frames)}\n")
            f.write(f"Duration: {duration:.2f}s\n")
            f.write("Music Sequence:\n")
            for i, fruit in enumerate(game_state.played_fruits):
                f.write(f"{i+1}. {fruit['pitch']} (Image: {fruit['name']})\n")
        
        # 验证文件是否成功创建
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            print(f"✅ Video saved successfully!")
            print(f"📁 Location: {video_path}")
            print(f"📊 File size: {file_size / 1024 / 1024:.2f} MB")
            return True, video_path
        else:
            print(f"❌ File was not created: {video_path}")
            return False, "File creation failed"
            
    except Exception as e:
        print(f"❌ Error saving video: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def play_recording():
    """播放录制的序列"""
    if game_state.played_fruits:
        for fruit_data in game_state.played_fruits:
            sounds[fruit_data["sound_index"]].play()
            pygame.time.delay(500)  # 每个音符间隔500ms

def main():
    """主函数"""
    global game_state
    
    # 启用文本输入（初始状态进入编辑模式）
    pygame.key.start_text_input()
    
    # 游戏主循环
    clock = pygame.time.Clock()
    running = True
    
    while running:
        current_time = pygame.time.get_ticks()
        
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.KEYDOWN:
                # 处理文本输入
                if game_state.editing_name:
                    if event.key == pygame.K_ESCAPE:
                        # 取消输入
                        game_state.editing_name = False
                        game_state.name_input = ""
                        game_state.cursor_position = 0
                        game_state.selection_start = 0
                        game_state.selection_end = 0
                        # 关闭文本输入
                        pygame.key.stop_text_input()
                    elif event.key == pygame.K_BACKSPACE:
                        # 删除字符
                        if game_state.selection_start != game_state.selection_end:
                            # 删除选中的文字
                            sel_start = min(game_state.selection_start, game_state.selection_end)
                            sel_end = max(game_state.selection_start, game_state.selection_end)
                            game_state.name_input = game_state.name_input[:sel_start] + game_state.name_input[sel_end:]
                            game_state.cursor_position = sel_start
                            game_state.selection_start = sel_start
                            game_state.selection_end = sel_start
                        elif game_state.cursor_position > 0:
                            game_state.name_input = game_state.name_input[:game_state.cursor_position-1] + game_state.name_input[game_state.cursor_position:]
                            game_state.cursor_position -= 1
                            game_state.selection_start = game_state.cursor_position
                            game_state.selection_end = game_state.cursor_position
                    elif event.key == pygame.K_DELETE:
                        # 删除光标后的字符
                        if game_state.selection_start != game_state.selection_end:
                            # 删除选中的文字
                            sel_start = min(game_state.selection_start, game_state.selection_end)
                            sel_end = max(game_state.selection_start, game_state.selection_end)
                            game_state.name_input = game_state.name_input[:sel_start] + game_state.name_input[sel_end:]
                            game_state.cursor_position = sel_start
                            game_state.selection_start = sel_start
                            game_state.selection_end = sel_start
                        elif game_state.cursor_position < len(game_state.name_input):
                            game_state.name_input = game_state.name_input[:game_state.cursor_position] + game_state.name_input[game_state.cursor_position+1:]
                    elif event.key == pygame.K_LEFT:
                        # 移动光标向左
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            # Shift+Left: 扩展选择
                            if game_state.cursor_position > 0:
                                game_state.cursor_position -= 1
                                game_state.selection_end = game_state.cursor_position
                        else:
                            # 单独Left: 移动光标
                            if game_state.cursor_position > 0:
                                game_state.cursor_position -= 1
                            game_state.selection_start = game_state.cursor_position
                            game_state.selection_end = game_state.cursor_position
                    elif event.key == pygame.K_RIGHT:
                        # 移动光标向右
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                            # Shift+Right: 扩展选择
                            if game_state.cursor_position < len(game_state.name_input):
                                game_state.cursor_position += 1
                                game_state.selection_end = game_state.cursor_position
                        else:
                            # 单独Right: 移动光标
                            if game_state.cursor_position < len(game_state.name_input):
                                game_state.cursor_position += 1
                            game_state.selection_start = game_state.cursor_position
                            game_state.selection_end = game_state.cursor_position
                    elif event.key == pygame.K_HOME:
                        # 移动到开头
                        game_state.cursor_position = 0
                        if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                            game_state.selection_start = 0
                        game_state.selection_end = 0
                    elif event.key == pygame.K_END:
                        # 移动到结尾
                        game_state.cursor_position = len(game_state.name_input)
                        if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                            game_state.selection_start = game_state.cursor_position
                        game_state.selection_end = game_state.cursor_position
                    elif event.key == pygame.K_a and (pygame.key.get_mods() & pygame.KMOD_META or pygame.key.get_mods() & pygame.KMOD_CTRL):
                        # Cmd+A / Ctrl+A: 全选
                        game_state.selection_start = 0
                        game_state.selection_end = len(game_state.name_input)
                        game_state.cursor_position = game_state.selection_end
                
                # 处理按键事件（音符输入）
                elif not game_state.editing_name and not game_state.on_start_page:
                    if event.key in note_fruits:
                        # 检查是否已输入作品名
                        if not game_state.name_entered:
                            # 如果还没输入名称，显示提示
                            game_state.save_success = False
                            game_state.save_message = "Please enter a work name first!\nClick the name box above to start."
                            game_state.save_message_timer = pygame.time.get_ticks()
                            game_state.popup_animation_start = pygame.time.get_ticks()
                            continue
                        
                        # 第一次按键时开始录制
                        if not game_state.recording_video:
                            game_state.recording_video = True
                            game_state.recording_start_time = pygame.time.get_ticks()
                        
                        # 播放音符并记录emoji
                        fruit_data = note_fruits[event.key].copy()  # 复制字典避免修改原始数据
                        sounds[fruit_data["sound_index"]].play()
                        game_state.played_fruits.append(fruit_data)
                        game_state.audio_data.append(fruit_data["sound_index"])
                        
                        # 记录音频事件时间戳（如果正在录制）
                        if game_state.recording_video and game_state.recording_start_time is not None:
                            timestamp = (pygame.time.get_ticks() - game_state.recording_start_time) / 1000.0  # 转换为秒
                            game_state.audio_events.append((timestamp, fruit_data["sound_index"]))
                        
                        # 立即在右侧生成emoji
                        emoji_data = fruit_data.copy()
                        emoji_data["random_display_size"] = random.randint(40, 80)  # 随机大小40-80
                        emoji_data["random_angle"] = random.randint(-30, 30)  # 随机旋转角度-30到30度
                        emoji_data["animation_start"] = pygame.time.get_ticks()  # 记录动画开始时间
                        
                        # 尝试找到不重叠的位置
                        max_attempts = 50
                        for attempt in range(max_attempts):
                            temp_x = random.randint(640 + 20, 640 + 500 - 80)
                            temp_y = random.randint(210 + 20, 210 + 400 - 80)
                            
                            # 检查是否与已放置的emoji重叠
                            is_overlapping = False
                            for pos in game_state.placed_positions:
                                # 计算两个emoji中心点之间的距离
                                center1_x = temp_x + emoji_data["random_display_size"] // 2
                                center1_y = temp_y + emoji_data["random_display_size"] // 2
                                center2_x = pos["x"] + pos["size"] // 2
                                center2_y = pos["y"] + pos["size"] // 2
                                
                                distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
                                min_distance = (emoji_data["random_display_size"] + pos["size"]) // 2 + 10  # 增加10像素间隙
                                
                                if distance < min_distance:
                                    is_overlapping = True
                                    break
                            
                            if not is_overlapping:
                                # 找到了不重叠的位置
                                emoji_data["random_x"] = temp_x
                                emoji_data["random_y"] = temp_y
                                game_state.placed_positions.append({
                                    "x": temp_x,
                                    "y": temp_y,
                                    "size": emoji_data["random_display_size"]
                                })
                                break
                        else:
                            # 如果尝试多次仍未找到位置，使用随机位置（容错机制）
                            emoji_data["random_x"] = random.randint(640 + 20, 640 + 500 - 80)
                            emoji_data["random_y"] = random.randint(210 + 20, 210 + 400 - 80)
                        
                        game_state.right_emojis_to_show.append(emoji_data)
                
                # 回车键处理（确认名称输入）- 适配 iOS、Windows、macOS
                if event.key == pygame.K_RETURN:
                    if game_state.editing_name:
                        # 如果正在编辑名称，确认输入
                        if game_state.name_input.strip():
                            game_state.song_name = game_state.name_input.strip()
                            game_state.name_entered = True  # 标记名称已输入
                        game_state.editing_name = False
                        game_state.name_input = ""
                        game_state.cursor_position = 0
                        game_state.selection_start = 0
                        game_state.selection_end = 0
                        pygame.key.stop_text_input()
                
                # 空格键处理（结束录制）
                if event.key == pygame.K_SPACE:
                    if not game_state.editing_name and game_state.recording_video and not game_state.on_start_page:
                        # 停止所有正在播放的音乐
                        pygame.mixer.stop()
                        # 如果正在录制且不在编辑名称，结束录制
                        game_state.recording_video = False
                        print("🎬 Recording finished! Click Download & Save to save your video.")
                
                # 其他控制键
                if not game_state.editing_name and not game_state.on_start_page:
                    # 重新开始第二页（保留作品名）
                    if event.key == pygame.K_r:
                        # 清除游戏状态，但保留作品名
                        saved_name = game_state.song_name
                        game_state.video_frames = []
                        game_state.frame_timestamps = []
                        game_state.recording_start_time = None
                        game_state.audio_events = []
                        game_state.played_fruits = []
                        game_state.right_emojis_to_show = []
                        game_state.placed_positions = []
                        game_state.recording_video = False
                        game_state.save_message = ""
                        game_state.song_name = saved_name  # 保留作品名
                        game_state.name_entered = True  # 保持名称已输入状态
                        print("🔄 Restarting page 2 (work name preserved)...")
                    
                    # 播放录制
                    if event.key == pygame.K_p:
                        play_recording()
                    
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 如果在开始页面
                if game_state.on_start_page:
                    # 检查是否点击了Start按钮
                    if game_state.start_button_rect and game_state.start_button_rect.collidepoint(event.pos):
                        if len(game_state.song_name.strip()) > 0:
                            # 名称已输入，可以开始
                            game_state.on_start_page = False
                            game_state.editing_name = False
                            game_state.name_entered = True
                            pygame.key.stop_text_input()
                    else:
                        # 检查是否点击了名称输入框
                        name_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 - 80, 400, 50)
                        if name_rect.collidepoint(event.pos):
                            if not game_state.editing_name:
                                game_state.editing_name = True
                                game_state.name_input = game_state.song_name
                                game_state.cursor_position = len(game_state.name_input)
                                game_state.selection_start = game_state.cursor_position
                                game_state.selection_end = game_state.cursor_position
                                pygame.key.start_text_input()
                        else:
                            # 点击其他地方，结束编辑
                            if game_state.editing_name:
                                if game_state.name_input.strip():
                                    game_state.song_name = game_state.name_input.strip()
                                game_state.editing_name = False
                                game_state.name_input = ""
                                game_state.cursor_position = 0
                                game_state.selection_start = 0
                                game_state.selection_end = 0
                                pygame.key.stop_text_input()
                    continue
                
                # 第二页：检查是否点击了返回箭头
                if game_state.back_arrow_rect and game_state.back_arrow_rect.collidepoint(event.pos):
                    # 返回到开始页面，保留作品名称
                    game_state.on_start_page = True
                    game_state.editing_name = True  # 进入编辑模式
                    game_state.name_entered = False  # 重置标记
                    game_state.recording_video = False  # 停止录制
                    # 清空录制数据
                    game_state.video_frames = []
                    game_state.frame_timestamps = []
                    game_state.recording_start_time = None
                    game_state.audio_events = []
                    game_state.played_fruits = []
                    game_state.right_emojis_to_show = []
                    game_state.placed_positions = []
                    # 保留作品名称，设置输入框状态
                    game_state.name_input = game_state.song_name
                    game_state.cursor_position = len(game_state.name_input)
                    game_state.selection_start = game_state.cursor_position
                    game_state.selection_end = game_state.cursor_position
                    pygame.key.start_text_input()
                    continue
                
                # 检查是否有消息弹窗正在显示，如果有则关闭
                if game_state.save_message and pygame.time.get_ticks() - game_state.save_message_timer < 3000:
                    game_state.save_message = ""
                    continue
                
                # 检查是否点击了下载按钮
                if game_state.download_button_rect:
                    if game_state.download_button_rect.collidepoint(event.pos):
                        if not game_state.recording_video:
                            success, result_info = save_work()
                            if success:
                                game_state.save_success = True
                                game_state.save_message = f"Video saved to: {result_info}"
                                game_state.save_message_timer = pygame.time.get_ticks()
                                game_state.popup_animation_start = pygame.time.get_ticks()
                                print("✅ Video saved successfully!")
                            else:
                                game_state.save_success = False
                                game_state.save_message = "Save failed! Please check:\n1. Did you press Space key to finish recording?\n2. Do you have write permission?\n3. Is there enough disk space?\nPlease try again or contact support."
                                game_state.save_message_timer = pygame.time.get_ticks()
                                game_state.popup_animation_start = pygame.time.get_ticks()
                                print(f"❌ Failed to save video: {result_info}")
                        else:
                            game_state.save_success = False
                            game_state.save_message = "Please press Space key to finish recording first!"
                            game_state.save_message_timer = pygame.time.get_ticks()
                            game_state.popup_animation_start = pygame.time.get_ticks()
                        continue
                
                # 第二页不允许编辑名称（已删除点击名称框的处理）
            
            elif event.type == pygame.TEXTINPUT:
                # 处理文本输入（支持中文输入法）
                if game_state.editing_name:
                    input_text = event.text
                    # 添加字符
                    if len(game_state.name_input) < 30 and input_text.isprintable():  # 限制最大长度
                        # 如果有选中的文字，先删除
                        if game_state.selection_start != game_state.selection_end:
                            sel_start = min(game_state.selection_start, game_state.selection_end)
                            sel_end = max(game_state.selection_start, game_state.selection_end)
                            game_state.name_input = game_state.name_input[:sel_start] + input_text + game_state.name_input[sel_end:]
                            game_state.cursor_position = sel_start + len(input_text)
                        else:
                            game_state.name_input = game_state.name_input[:game_state.cursor_position] + input_text + game_state.name_input[game_state.cursor_position:]
                            game_state.cursor_position += len(input_text)
                        game_state.selection_start = game_state.cursor_position
                        game_state.selection_end = game_state.cursor_position
        
        # 绘制界面
        screen.fill(BACKGROUND)
        
        if game_state.on_start_page:
            # 绘制开始页面
            draw_start_page()
        else:
            # 绘制游戏主界面
            # 绘制返回箭头（左上角）
            draw_back_arrow()
            
            # 绘制作品名称显示（只读）
            draw_song_name_input()
            
            # 始终显示左右两个框
            draw_canvas()
            draw_statistics()
            
            # 绘制下载按钮（一直显示）
            game_state.download_button_rect = draw_download_button()
            
            # 绘制控制说明
            draw_controls()
            
            # 绘制保存成功消息弹窗（最后绘制，在所有内容之上）
            draw_save_message()
        
        pygame.display.flip()
        
        # 录制视频帧
        if game_state.recording_video:
            if game_state.recording_start_time is None:
                game_state.recording_start_time = pygame.time.get_ticks()
            
            # 捕获当前屏幕（裁剪掉顶部40px和Download按钮及以下内容）
            # 顶部裁剪40px，底部裁剪到620
            crop_top = 40
            crop_height = 620 - crop_top  # 580像素高度
            
            # 创建一个子表面来捕获裁剪区域
            cropped_surface = screen.subsurface(pygame.Rect(0, crop_top, WIDTH, crop_height))
            frame = pygame.surfarray.array3d(cropped_surface)
            frame = np.transpose(frame, (1, 0, 2))  # 转换坐标轴
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # RGB转BGR
            game_state.video_frames.append(frame)
            game_state.frame_timestamps.append(pygame.time.get_ticks() - game_state.recording_start_time)
        
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
