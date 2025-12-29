"""
生成应用图标

运行方式: python create_icon.py
需要安装: pip install pillow
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # 创建 256x256 的图像
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 绘制圆角矩形背景（渐变效果用纯色代替）
    # 使用蓝紫色渐变的中间色
    bg_color = (102, 126, 234)  # #667eea

    # 绘制圆形背景
    margin = 10
    draw.ellipse([margin, margin, size-margin, size-margin], fill=bg_color)

    # 绘制文字 "公文"
    try:
        # 尝试使用系统中文字体
        font = ImageFont.truetype("msyh.ttc", 80)  # 微软雅黑
    except:
        try:
            font = ImageFont.truetype("simhei.ttf", 80)  # 黑体
        except:
            font = ImageFont.load_default()

    text = "公文"

    # 获取文字边界框
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # 居中绘制
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 10

    draw.text((x, y), text, fill='white', font=font)

    # 保存为 ICO
    icon_path = os.path.join(os.path.dirname(__file__), 'app.ico')

    # 创建多尺寸图标
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    imgs = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]

    imgs[0].save(icon_path, format='ICO', sizes=[(s[0], s[1]) for s in sizes], append_images=imgs[1:])

    print(f"图标已生成: {icon_path}")

if __name__ == '__main__':
    create_icon()
