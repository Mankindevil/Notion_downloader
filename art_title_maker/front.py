import os
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ==================== 配置区域 ====================
WIDTH = 3840
HEIGHT = 2160
DPI = (500, 500)
FONT_FILE = "Chewy-Regular.ttf"

# --- 颜色定义 (全部转为 RGBA 元组) ---
# 文字颜色 (荧光青柠) - 对应 HTML 中的 --green-lime: #c6ff00
COLOR_LIME = (198, 255, 0, 255) 
# 阴影颜色 (深蓝，不透明度约 60%) -> 原来的硬阴影
COLOR_SHADOW = (66, 100, 250, 255) # 稍微实一点，因为后面会通过图层透明度控制
# 波浪线颜色 (半透明白) - 对应 HTML 中的 rgba(255,255,255,0.4)
COLOR_WAVE = (255, 255, 255, 102)  # 0.4 * 255 ≈ 102

# 爱心颜色池 (您指定的颜色 + 透明度)
HEART_PALETTE = [
    (244, 255, 129, 255),  # COLOR_PALE (实心嫩黄)
    (255, 255, 255, 255),  # COLOR_WHITE (实心白)
    (255, 255, 255, 150)   # 半透明白
]

def create_transparent_canvas():
    return Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))

def load_local_font(filename, size):
    if not os.path.exists(filename):
        print("警告：使用默认字体。")
        return ImageFont.load_default()
    return ImageFont.truetype(filename, size)

# ==================== 绘制组件 ====================

def create_heart_sprite(size, color):
    """
    创建一个带阴影的爱心 '精灵' 图片
    """
    w = int(size * 1.5)
    h = int(size * 1.5)
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    
    # 内部函数：画爱心路径
    def draw_heart_shape(draw_obj, offset_x, offset_y, fill_color):
        s = size
        # 几何参数
        # 左圆
        draw_obj.ellipse((offset_x, offset_y, offset_x + s*0.5, offset_y + s*0.5), fill=fill_color)
        # 右圆
        draw_obj.ellipse((offset_x + s*0.5, offset_y, offset_x + s, offset_y + s*0.5), fill=fill_color)
        # 倒三角
        triangle = [
            (offset_x + s*0.05, offset_y + s*0.35),
            (offset_x + s*0.95, offset_y + s*0.35),
            (offset_x + s*0.5, offset_y + s*0.95)
        ]
        draw_obj.polygon(triangle, fill=fill_color)

    # 1. 先画阴影 (向右下偏移)
    shadow_offset = size * 0.15
    # 阴影也是半透明的
    shadow_color = (66, 100, 250, 150) 
    draw_heart_shape(d, shadow_offset + size*0.1, shadow_offset + size*0.1, shadow_color)
    
    # 2. 再画本体 (盖在阴影上面)
    draw_heart_shape(d, size*0.1, size*0.1, color)
    
    return img

def draw_wavy_line_unicode(x_center, y_center, font_size, color):
    """
    使用 Unicode 波浪线符号绘制（对应 HTML 中的 "〰〰〰"）
    对应 HTML: content: "〰〰〰"; font-size: 24px; letter-spacing: -3px; transform: rotate(-5deg);
    如果字体不支持，则使用路径绘制模拟波浪线
    """
    # Unicode 波浪线符号
    wave_chars = "〰〰〰"
    
    # 尝试加载支持 Unicode 的字体
    wave_font = None
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑（支持 Unicode）
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "C:/Windows/Fonts/arial.ttf",  # Arial
        "arial.ttf",
    ]
    
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                wave_font = ImageFont.truetype(font_path, font_size)
                break
        except:
            continue
    
    # 如果都失败了，尝试使用默认字体
    if wave_font is None:
        try:
            wave_font = ImageFont.load_default()
        except:
            wave_font = ImageFont.load_default()
    
    # 创建临时图像来绘制和旋转（足够大的画布）
    temp_img = Image.new("RGBA", (int(font_size * 8), int(font_size * 3)), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    
    # 测试字符是否能正确渲染
    test_char = "〰"
    test_bbox = temp_draw.textbbox((0, 0), test_char, font=wave_font)
    char_width = test_bbox[2] - test_bbox[0]
    char_height = test_bbox[3] - test_bbox[1]
    
    # 如果字符宽度为0或太小，说明字体不支持，使用路径绘制备选方案
    use_path_fallback = char_width < font_size * 0.1
    
    if use_path_fallback:
        # 使用路径绘制连续的波浪线（模拟 "〰〰〰" 效果）
        # 计算总宽度（对应3个紧密的波浪）
        total_width = font_size * 3.5
        # 确保波浪线在图像中心
        start_x = temp_img.width // 2 - total_width // 2
        y_pos = temp_img.height // 2
        
        # 绘制一条连续的波浪线（3个完整周期）
        wave_amplitude = font_size * 0.15  # 波浪幅度
        wave_length = total_width / 3.0  # 每个波浪的长度（3个完整周期）
        
        # 绘制一条连续的波浪线，确保对称
        points = []
        steps = int(total_width / 1.5)  # 足够的采样点保证平滑
        for i in range(steps + 1):
            x = start_x + (i / steps) * total_width
            # 使用3个完整周期的正弦波，确保连续
            # 从0相位开始，确保对称（中间点在y_pos）
            phase = (x - start_x) / wave_length * 2 * math.pi
            y = y_pos + wave_amplitude * math.sin(phase)
            points.append((x, y))
        
        # 绘制连续的波浪线
        temp_draw.line(points, fill=color, width=int(font_size * 0.15), joint="curve")
    else:
        # 使用 Unicode 字符绘制
        # 计算 letter-spacing（负间距，让字符更紧密）
        letter_spacing = -int(font_size * 3 / 24)  # 按比例缩放
        
        # 计算总宽度
        total_width = char_width * len(wave_chars) + letter_spacing * (len(wave_chars) - 1)
        
        # 在临时图像中心开始绘制
        start_x = temp_img.width // 2 - total_width // 2
        y_pos = temp_img.height // 2
        
        # 逐个字符绘制，应用 letter-spacing
        x_offset = start_x
        for i, char in enumerate(wave_chars):
            try:
                temp_draw.text((x_offset, y_pos), char, font=wave_font, fill=color, anchor="mm")
            except Exception as e:
                try:
                    temp_draw.text((x_offset, y_pos - char_height // 2), char, font=wave_font, fill=color)
                except:
                    print(f"无法绘制字符 {char}: {e}")
            x_offset += char_width + letter_spacing
    
    # 裁剪到实际内容区域
    try:
        bbox = temp_img.getbbox()
        if bbox and bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            margin = 10
            temp_img = temp_img.crop((
                max(0, bbox[0] - margin),
                max(0, bbox[1] - margin),
                min(temp_img.width, bbox[2] + margin),
                min(temp_img.height, bbox[3] + margin)
            ))
        else:
            print("警告：无法获取波浪线边界框，使用完整图像")
    except Exception as e:
        print(f"裁剪波浪线时出错: {e}")
    
    # 裁剪到实际内容区域
    try:
        bbox = temp_img.getbbox()
        if bbox and bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            margin = 10
            temp_img = temp_img.crop((
                max(0, bbox[0] - margin),
                max(0, bbox[1] - margin),
                min(temp_img.width, bbox[2] + margin),
                min(temp_img.height, bbox[3] + margin)
            ))
        else:
            print("警告：无法获取波浪线边界框，使用完整图像")
    except Exception as e:
        print(f"裁剪波浪线时出错: {e}")
    
    # 旋转 -5 度（对应 HTML 的 transform: rotate(-5deg)）
    # 旋转图像，使用中心点旋转
    rotated_temp = temp_img.rotate(-5, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
    
    # 计算粘贴位置（确保波浪线的中心点与 x_center, y_center 对齐）
    # 由于旋转时使用了expand=True，图像会变大，但中心点位置保持不变
    paste_x = int(x_center - rotated_temp.width // 2)
    paste_y = int(y_center - rotated_temp.height // 2)
    
    return rotated_temp, paste_x, paste_y

# ==================== 主逻辑 ====================

def generate_final_fixed():
    print("正在生成 Style6 风格 (快乐蜡笔 Crayon) - 手绘波浪线 + 调整爱心位置...")
    
    # 1. 字体
    font_main = load_local_font(FONT_FILE, 550)
    font_amp = load_local_font(FONT_FILE, 280)
    
    img = create_transparent_canvas()
    
    # ================== 文字部分 (Skew + Rotate + Hard Shadow) ==================
    
    # 创建临时大画布防止变换时被切
    temp_size = 5000
    txt_layer = Image.new("RGBA", (temp_size, temp_size), (0,0,0,0))
    d_txt = ImageDraw.Draw(txt_layer)
    tcx, tcy = temp_size // 2, temp_size // 2
    
    # 绘制原始文字
    lines = [
        ("NOZOMI", -400, font_main),
        ("&", 0, font_amp), 
        ("HIKARI", 400, font_main)
    ]
    
    text_bounds = {} # 记录位置供后续使用
    
    for text, y_off, font in lines:
        d_txt.text((tcx, tcy + y_off), text, font=font, fill=COLOR_LIME, anchor="mm")
        # 记录简单的边界框
        bbox = d_txt.textbbox((tcx, tcy + y_off), text, font=font, anchor="mm")
        text_bounds[text] = bbox

    # --- 变换 1: Skew (倾斜) ---
    # x' = x - 0.1 * y (模拟 CSS skewX(-5deg))
    skew_matrix = (1, -0.1, 0, 0, 1, 0)
    txt_transformed = txt_layer.transform(
        (temp_size, temp_size), 
        Image.AFFINE, 
        skew_matrix, 
        resample=Image.BICUBIC
    )
    
    # --- 变换 2: Rotate (旋转) ---
    # 逆时针旋转 2 度，稍微上扬
    txt_transformed = txt_transformed.rotate(2, resample=Image.BICUBIC, center=(tcx, tcy))
    
    # 裁剪回 4K 画布
    crop_box = (
        tcx - WIDTH//2, tcy - HEIGHT//2,
        tcx + WIDTH//2, tcy + HEIGHT//2
    )
    txt_final = txt_transformed.crop(crop_box)
    
    # --- 生成硬阴影 ---
    alpha = txt_final.split()[3]
    shadow_layer = Image.new("RGBA", (WIDTH, HEIGHT), COLOR_SHADOW)
    shadow_layer.putalpha(alpha)
    
    # 阴影错位 (HTML 是右下偏移)
    offset_shadow = 18 
    
    # 贴上去：先阴影，再文字
    img.paste(shadow_layer, (offset_shadow, offset_shadow), shadow_layer)
    img.paste(txt_final, (0, 0), txt_final)
    
    # 计算文字在最终画布上的实际位置（用于避开爱心）
    # 由于经过了变换和裁剪，需要计算实际位置
    cx, cy = WIDTH // 2, HEIGHT // 2
    # NOZOMI 大约在中心偏左上
    nozomi_center_x = cx - 750
    nozomi_center_y = cy - 600
    # HIKARI 大约在中心偏右下
    hikari_center_x = cx + 750
    hikari_center_y = cy + 400
    
    # ================== 装饰：爱心簇 (不重叠 + 带阴影) ==================
    
    placed_items = [] # 用于碰撞检测 [(x, y, radius), ...]

    def place_hearts_no_overlap(center_x, center_y, count, spread_r):
        attempts = 0
        added = 0
        while added < count and attempts < 200:
            attempts += 1
            # 随机极坐标位置
            r = random.uniform(0, spread_r)
            theta = random.uniform(0, 2*math.pi)
            
            hx = center_x + r * math.cos(theta)
            hy = center_y + r * math.sin(theta)
            
            size = random.randint(35, 60) # 爱心大小
            hit_radius = size * 0.8       # 碰撞半径
            
            # 碰撞检测
            overlap = False
            for px, py, pr in placed_items:
                dist = math.sqrt((hx - px)**2 + (hy - py)**2)
                if dist < (hit_radius + pr): # 如果距离小于两者半径之和，重叠
                    overlap = True
                    break
            
            if not overlap:
                # 生成爱心精灵
                color = random.choice(HEART_PALETTE)
                heart_sprite = create_heart_sprite(size, color)
                
                # 随机旋转
                rot = random.randint(-30, 30)
                heart_sprite = heart_sprite.rotate(rot, resample=Image.BICUBIC, expand=True)
                
                # 贴图
                paste_x = int(hx - heart_sprite.width // 2)
                paste_y = int(hy - heart_sprite.height // 2)
                img.paste(heart_sprite, (paste_x, paste_y), heart_sprite)
                
                placed_items.append((hx, hy, hit_radius))
                added += 1

    # 计算簇的中心点 (根据变换后的视觉位置调整)
    # NOZOMI 左上 - 保持原位置
    nx = nozomi_center_x
    ny = nozomi_center_y
    place_hearts_no_overlap(nx, ny, count=8, spread_r=250)
    
    # HIKARI 右下 - 调整位置，避免和文字重叠
    # 将爱心簇移到 HIKARI 的右侧，而不是下方
    hx = hikari_center_x + 400  # 向右偏移更多
    hy = hikari_center_y - 100  # 稍微上移，避免和文字重叠
    place_hearts_no_overlap(hx, hy, count=8, spread_r=250)
    
    # ================== 装饰：Unicode 波浪线符号 ==================
    # 对应 HTML 中的波浪线装饰，位置在 HIKARI 下方
    # HTML: content: "〰〰〰"; font-size: 24px; letter-spacing: -3px; transform: rotate(-5deg);
    # HTML 中波浪线在 bottom: 25px，相对于卡片底部（卡片高度约 220px）
    
    # 波浪线位置：在 HIKARI 文字正下方
    wave_cx = hikari_center_x  # 与 HIKARI 文字中心对齐（水平居中）
    
    # 计算 HIKARI 文字底部位置
    # HIKARI 中心在 hikari_center_y，文字高度约 550px，所以底部在 center_y + 275
    font_main_size = 550
    hikari_bottom = hikari_center_y + int(font_main_size * 0.5)
    
    # HTML 中波浪线在 bottom: 25px，相对于卡片底部（卡片高度约220px）
    # 文字在卡片中心，所以波浪线应该在文字下方不远处
    # 按比例缩放：HTML 中约 25px 间距，我们按比例放大
    spacing = int(550 * 25 / 48)  # 约 25px 间距（按比例），更接近 HTML
    wave_cy = hikari_bottom + spacing
    
    # 绘制 Unicode 波浪线符号（对应 HTML 中的 24px，但需要按比例放大）
    wave_font_size = int(550 * 24 / 48)  # 按比例缩放（HTML 中文字是 48px，波浪线是 24px）
    
    try:
        wave_img, wave_x, wave_y = draw_wavy_line_unicode(
            wave_cx, wave_cy, wave_font_size, COLOR_WAVE
        )
        
        # 确保粘贴位置在画布范围内
        if wave_img.width > 0 and wave_img.height > 0:
            # 限制在画布范围内（但允许稍微超出，因为旋转后可能需要更多空间）
            wave_x = max(-wave_img.width//2, min(wave_x, WIDTH - wave_img.width//2))
            wave_y = max(-wave_img.height//2, min(wave_y, HEIGHT - wave_img.height//2))
            img.paste(wave_img, (wave_x, wave_y), wave_img)
        else:
            print("警告：波浪线图像为空")
    except Exception as e:
        print(f"绘制波浪线时出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 保存
    outfile = "nozomi_hikari_final_v2.png"
    img.save(outfile, dpi=DPI)
    print(f"完成！图片已保存至: {outfile}")

if __name__ == "__main__":
    # 随机种子 1024 出来的爱心分布比较好看
    random.seed(1024) 
    generate_final_fixed()