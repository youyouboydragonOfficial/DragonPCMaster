from PIL import Image, ImageDraw, ImageFont
import math

def create_dragon_icon():
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded diamond / shield
    cx, cy = 128, 128
    
    # Outer glow / shield
    points = [
        (cx, 16),
        (240, 72),
        (220, 200),
        (cx, 246),
        (36, 200),
        (16, 72)
    ]
    
    # Dark gaming shield background
    draw.polygon(points, fill=(13, 17, 23, 245), outline=(0, 240, 255, 255), width=4)
    
    # Inner border
    inner_points = [
        (cx, 32),
        (224, 82),
        (206, 190),
        (cx, 230),
        (50, 190),
        (32, 82)
    ]
    draw.polygon(inner_points, outline=(255, 0, 128, 180), width=2)

    # Dragon head stylized silhouette / cyber gaming pulse
    # Cyber Dragon horns & snout
    dragon_pts = [
        (128, 55),
        (165, 85),
        (150, 105),
        (185, 115),
        (155, 140),
        (175, 175),
        (128, 160),
        (81, 175),
        (101, 140),
        (71, 115),
        (106, 105),
        (91, 85)
    ]
    draw.polygon(dragon_pts, fill=(0, 255, 200, 230), outline=(0, 255, 255, 255), width=2)
    
    # Glowing eyes
    draw.ellipse([110, 115, 120, 125], fill=(255, 255, 0, 255))
    draw.ellipse([136, 115, 146, 125], fill=(255, 255, 0, 255))

    # Pulse waves (Hardware monitor pulse)
    pulse = [
        (45, 195),
        (95, 195),
        (110, 175),
        (128, 220),
        (146, 170),
        (161, 195),
        (211, 195)
    ]
    draw.line(pulse, fill=(0, 255, 255, 255), width=4)

    # Save PNG
    img.save("static/icon.png")
    
    # Save ICO
    img.save("static/icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("Icon generated successfully!")

if __name__ == "__main__":
    import os
    os.makedirs("static", exist_ok=True)
    create_dragon_icon()
