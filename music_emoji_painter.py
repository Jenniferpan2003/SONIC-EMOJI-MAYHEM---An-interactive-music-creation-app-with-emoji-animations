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
    """加载1.png到7.png图片文件"""
    images = {}
    for i in range(1, 8):  # 1-7对应Do-Si
        try:
            img_path = os.path.join(SCRIPT_DIR, f"{i}.png")
            img = pygame.image.load(img_path)
            # 缩放图片到合适大小
            img = pygame.transform.scale(img, (50, 50))
            images[i] = img
        except pygame.error as e:
            print(f"Cannot load image {i}.png: {e}")
            images[i] = None
    return images

# 加载所有图片
fruit_images = load_images()

# 音符到emoji的映射
note_fruits = {
    pygame.K_1: {"name": "1", "image": fruit_images[1], "color": (144, 238, 144), "pitch": "Do", "sound_index": 0},
    pygame.K_2: {"name": "2", "image": fruit_images[2], "color": (255, 99, 71), "pitch": "Re", "sound_index": 1},
    pygame.K_3: {"name": "3", "image": fruit_images[3], "color": (255, 165, 0), "pitch": "Mi", "sound_index": 2},
    pygame.K_4: {"name": "4", "image": fruit_images[4], "color": (255, 255, 0), "pitch": "Fa", "sound_index": 3},
    pygame.K_5: {"name": "5", "image": fruit_images[5], "color": (147, 112, 219), "pitch": "Sol", "sound_index": 4},
    pygame.K_6: {"name": "6", "image": fruit_images[6], "color": (255, 20, 147), "pitch": "La", "sound_index": 5},
    pygame.K_7: {"name": "7", "image": fruit_images[7], "color": (70, 130, 180), "pitch": "Si", "sound_index": 6},
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

# 创建音效 - C4到B4音阶
sounds = []
frequencies = [262, 294, 330, 349, 392, 440, 494]  # Do Re Mi Fa Sol La Si
for freq in frequencies:
    sounds.append(generate_tone(freq, 800))

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

game_state = GameState()

# 字体设置 - 使用自定义字体
ENGLISH_FONT_PATH = "/Users/a1/Desktop/polyu/5913周四/as3/led_counter-7.ttf"
CHINESE_FONT_PATH = "/Users/a1/Desktop/polyu/5913周四/as3/SourceHanSansCN-Bold.otf"

# 英文字体（LED样式）
try:
    title_font_en = pygame.font.Font(ENGLISH_FONT_PATH, 48)
    font_en = pygame.font.Font(ENGLISH_FONT_PATH, 32)
    small_font_en = pygame.font.Font(ENGLISH_FONT_PATH, 19)  # 24 - 5 = 19
    path_font_en = pygame.font.Font(ENGLISH_FONT_PATH, 18)
    english_font_loaded = True
except:
    print("English font not found, using system font")
    title_font_en = pygame.font.SysFont('arial', 48, bold=True)
    font_en = pygame.font.SysFont('arial', 32)
    small_font_en = pygame.font.SysFont('arial', 19)  # 24 - 5 = 19
    path_font_en = pygame.font.SysFont('arial', 18)
    english_font_loaded = False

# 中文字体（思源黑体）
try:
    title_font_cn = pygame.font.Font(CHINESE_FONT_PATH, 48)
    font_cn = pygame.font.Font(CHINESE_FONT_PATH, 32)
    small_font_cn = pygame.font.Font(CHINESE_FONT_PATH, 19)  # 24 - 5 = 19
    path_font_cn = pygame.font.Font(CHINESE_FONT_PATH, 18)
    chinese_font_loaded = True
except:
    print("Chinese font not found, using system font")
    title_font_cn = pygame.font.SysFont('microsoftyahei', 48, bold=True)
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
    label_y = 210 - 45  # 在框上方45像素
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
        image_y = 210 + 200 - 180  # 居中：210 + 400/2 - 360/2（Y坐标+10）
        screen.blit(big_image, (image_x, image_y))

def draw_statistics():
    """绘制统计信息"""
    # 绘制右侧标题 "Emoji Music Artwork"
    label_text = font_en.render("Emoji Music Artwork", True, TEXT_COLOR)
    label_x = 640 + 250 - label_text.get_width() // 2  # 居中：640 + 500/2
    label_y = 210 - 45  # 在框上方45像素
    screen.blit(label_text, (label_x, label_y))
    
    stats_rect = pygame.Rect(640, 210, 500, 400)  # 右侧统计框位置：向下移动10像素（200+10=210）
    pygame.draw.rect(screen, CANVAS_BG, stats_rect, border_radius=10)
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

def draw_controls():
    """绘制控制说明"""
    controls_y = 715
    controls_text = [
        "Step 1: Enter your work name | Step 2: Press 1-7 to play emoji music | Press Space to finish, then download!",
        "Press R to restart"
    ]
    
    for i, text in enumerate(controls_text):
        control_text = small_font.render(text, True, (100, 100, 100))
        screen.blit(control_text, (WIDTH//2 - control_text.get_width()//2, controls_y + i * 30))

def draw_song_name_input():
    """绘制歌曲名称输入框"""
    name_rect = pygame.Rect(WIDTH//2 - 200, 100, 400, 40)
    
    # 根据是否正在编辑改变背景色
    if game_state.editing_name:
        pygame.draw.rect(screen, (255, 255, 200), name_rect, border_radius=10)  # 黄色背景表示正在编辑
        pygame.draw.rect(screen, (255, 165, 0), name_rect, 3, border_radius=10)  # 橙色边框
    else:
        pygame.draw.rect(screen, (255, 255, 255), name_rect, border_radius=10)  # 白色背景
        pygame.draw.rect(screen, TEXT_COLOR, name_rect, 2, border_radius=10)  # 普通边框
    
    # 显示当前文字
    display_text = game_state.name_input if game_state.editing_name else game_state.song_name
    
    # 绘制文字（居中）- 使用混合字体
    name_text = render_mixed_text(display_text, font_en, font_cn, TEXT_COLOR)
    text_x = name_rect.centerx - name_text.get_width() // 2
    text_y = name_rect.y + 5
    
    # 如果正在编辑，绘制选择高亮和光标
    if game_state.editing_name:
        # 检测是否包含中文，选择合适的字体
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in display_text)
        active_font = font_cn if has_chinese else font_en
        
        # 绘制选中区域
        if game_state.selection_start != game_state.selection_end:
            sel_start = min(game_state.selection_start, game_state.selection_end)
            sel_end = max(game_state.selection_start, game_state.selection_end)
            
            # 计算选中区域的位置
            before_sel = display_text[:sel_start]
            selected = display_text[sel_start:sel_end]
            
            before_width = active_font.render(before_sel, True, TEXT_COLOR).get_width()
            selected_width = active_font.render(selected, True, TEXT_COLOR).get_width()
            
            # 绘制选中背景
            sel_rect = pygame.Rect(text_x + before_width, text_y, selected_width, name_text.get_height())
            pygame.draw.rect(screen, (100, 150, 255), sel_rect)  # 蓝色选中背景
        
        # 绘制光标
        cursor_visible = (pygame.time.get_ticks() // 500) % 2  # 每500ms闪烁一次
        if cursor_visible and game_state.selection_start == game_state.selection_end:
            cursor_text = display_text[:game_state.cursor_position]
            cursor_x = text_x + active_font.render(cursor_text, True, TEXT_COLOR).get_width()
            pygame.draw.line(screen, TEXT_COLOR, (cursor_x, text_y), (cursor_x, text_y + name_text.get_height()), 2)
    
    # 绘制文字
    screen.blit(name_text, (text_x, text_y))
    
    # 提示文字（居中）- 使用更小的字体
    try:
        prompt_font = pygame.font.Font(ENGLISH_FONT_PATH, 22)  # 24 - 2 = 22
    except:
        prompt_font = pygame.font.SysFont('arial', 22)
    
    if game_state.editing_name:
        prompt_text = prompt_font.render("Type your work name (Press Enter to confirm, Esc to cancel)", True, (255, 100, 0))
    elif not game_state.name_entered:
        prompt_text = prompt_font.render("Click here to enter your work name first", True, (255, 0, 0))
    else:
        prompt_text = prompt_font.render("Click here to edit your work name", True, TEXT_COLOR)
    
    prompt_x = name_rect.centerx - prompt_text.get_width() // 2
    screen.blit(prompt_text, (prompt_x, name_rect.y - 25))
    
    return name_rect  # 返回矩形区域用于点击检测

def draw_save_message():
    """绘制保存消息弹窗"""
    if game_state.save_message and pygame.time.get_ticks() - game_state.save_message_timer < 5000:  # 显示5秒
        # 计算弹窗位置
        popup_width = 800
        popup_height = 200 if not game_state.save_success else 150
        popup_x = WIDTH//2 - popup_width//2
        popup_y = HEIGHT//2 - popup_height//2
        
        popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
        
        # 绘制半透明背景
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # 半透明黑色
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

        # 绘制标题文字
        title_surface = font.render(title_text, True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(popup_x + popup_width//2, popup_y + 35))
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
        
        # 绘制每行文字
        line_height = 22
        start_y = popup_y + 70
        for i, line in enumerate(lines):
            line_text = path_font.render(line, True, (255, 255, 255))
            line_rect = line_text.get_rect(center=(popup_x + popup_width//2, start_y + i * line_height))
            screen.blit(line_text, line_rect)
        
        # 绘制关闭提示
        close_text = small_font.render("(Click anywhere to close)", True, (200, 200, 200))
        close_rect = close_text.get_rect(center=(popup_x + popup_width//2, popup_y + popup_height - 25))
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
        pygame.draw.rect(screen, (255, 255, 255), hover_rect, 6, border_radius=10)  # 白色边框
        
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
        pygame.draw.rect(screen, (255, 255, 255), button_rect, 6, border_radius=10)  # 白色边框
        
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
    """生成音频轨道"""
    # 创建空的音频数组（双声道）
    num_samples = int(duration * sample_rate)
    audio_samples = np.zeros((num_samples, 2), dtype=np.int16)
    
    frequencies = [262, 294, 330, 349, 392, 440, 494]  # Do Re Mi Fa Sol La Si
    
    for timestamp, sound_index in audio_events:
        # 生成音符
        freq = frequencies[sound_index]
        note_duration = 0.8  # 800ms
        num_samples = int(note_duration * sample_rate)
        t = np.linspace(0, note_duration, num_samples, False)
        
        # 生成音符波形
        envelope = np.exp(-3 * t)  # 衰减包络
        note = (32767.0 * 0.3 * envelope * np.sin(2 * np.pi * freq * t)).astype(np.int16)
        
        # 计算插入位置
        start_sample = int(timestamp * sample_rate)
        end_sample = min(start_sample + num_samples, len(audio_samples))
        
        # 添加到音频轨道（立体声）
        if start_sample < len(audio_samples):
            audio_samples[start_sample:end_sample, 0] += note[:end_sample-start_sample]
            audio_samples[start_sample:end_sample, 1] += note[:end_sample-start_sample]
    
    # 转换为float格式 (-1.0 to 1.0)
    return audio_samples.astype(np.float32) / 32768.0

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
                elif not game_state.editing_name:
                    if event.key in note_fruits:
                        # 检查是否已输入作品名
                        if not game_state.name_entered:
                            # 如果还没输入名称，显示提示
                            game_state.save_success = False
                            game_state.save_message = "Please enter a work name first!\nClick the name box above to start."
                            game_state.save_message_timer = pygame.time.get_ticks()
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
                    if not game_state.editing_name and game_state.recording_video:
                        # 如果正在录制且不在编辑名称，结束录制
                        game_state.recording_video = False
                        print("🎬 Recording finished! Click Download & Save to save your video.")
                
                # 其他控制键
                if not game_state.editing_name:
                    # 重新开始
                    if event.key == pygame.K_r:
                        game_state = GameState()
                        # 重新启用文本输入（因为新的GameState进入编辑模式）
                        pygame.key.start_text_input()
                        
                    # 播放录制
                    if event.key == pygame.K_p:
                        play_recording()
                    
            elif event.type == pygame.MOUSEBUTTONDOWN:
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
                                print("✅ Video saved successfully!")
                            else:
                                game_state.save_success = False
                                game_state.save_message = "保存失败！请检查：\n1. 是否按下空格键结束录制\n2. 文件夹是否有写入权限\n3. 磁盘空间是否充足\n请重试或联系技术支持"
                                game_state.save_message_timer = pygame.time.get_ticks()
                                print(f"❌ Failed to save video: {result_info}")
                        else:
                            game_state.save_success = False
                            game_state.save_message = "请先按空格键结束录制！"
                            game_state.save_message_timer = pygame.time.get_ticks()
                        continue
                
                # 检查是否点击了歌曲名称输入框
                name_rect = pygame.Rect(WIDTH//2 - 200, 100, 400, 40)
                if name_rect.collidepoint(event.pos):
                    # 允许在以下情况编辑名称：1.初始状态（未输入名称） 2.录制结束后
                    if not game_state.editing_name and not game_state.recording_video:
                        # 开始编辑模式
                        game_state.editing_name = True
                        game_state.name_input = game_state.song_name
                        # 设置光标到文本末尾
                        game_state.cursor_position = len(game_state.name_input)
                        game_state.selection_start = game_state.cursor_position
                        game_state.selection_end = game_state.cursor_position
                        # 启用文本输入（支持输入法）
                        pygame.key.start_text_input()
                else:
                    # 点击其他地方，结束编辑模式
                    if game_state.editing_name:
                        if game_state.name_input.strip():
                            game_state.song_name = game_state.name_input.strip()
                            game_state.name_entered = True  # 标记名称已输入
                        game_state.editing_name = False
                        game_state.name_input = ""
                        game_state.cursor_position = 0
                        game_state.selection_start = 0
                        game_state.selection_end = 0
                        # 关闭文本输入
                        pygame.key.stop_text_input()
            
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
        
        # 绘制标题
        title = title_font.render("Music Emoji Painter", True, TEXT_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))
        
        # 绘制可编辑的歌曲名称输入框
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
            
            # 捕获当前屏幕
            frame = pygame.surfarray.array3d(screen)
            frame = np.transpose(frame, (1, 0, 2))  # 转换坐标轴
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # RGB转BGR
            game_state.video_frames.append(frame)
            game_state.frame_timestamps.append(pygame.time.get_ticks() - game_state.recording_start_time)
        
        clock.tick(60)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
