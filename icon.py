from PIL import Image, ImageDraw

def create_icon():
    # Create a 64x64 image with a transparent background
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a simple "T" shape
    draw.rectangle([16, 16, 48, 24], fill=(0, 120, 212))  # Top horizontal
    draw.rectangle([28, 16, 36, 48], fill=(0, 120, 212))  # Vertical
    
    # Save the icon
    img.save('icon.png')

if __name__ == "__main__":
    create_icon()