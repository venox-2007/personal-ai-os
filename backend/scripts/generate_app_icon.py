import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

def create_personal_ai_icon():
    size = 512
    # Create RGBA image with transparent background
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center = size / 2
    radius = size * 0.44

    # Outer soft glow
    glow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    glow_draw.ellipse(
        [center - radius - 10, center - radius - 10, center + radius + 10, center + radius + 10],
        fill=(0, 210, 255, 60),
    )
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(glow_img)

    # Base container: Sleek deep obsidian/midnight blue rounded disc
    # Gradient simulation from top-left (deep navy #111827) to bottom-right (#030712)
    base_mask = Image.new("L", (size, size), 0)
    base_mask_draw = ImageDraw.Draw(base_mask)
    base_mask_draw.ellipse(
        [center - radius, center - radius, center + radius, center + radius],
        fill=255,
    )

    base_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        factor = y / size
        # Subtle gradient from (15, 23, 42) slate-900 to (2, 6, 23) slate-950
        r = int(15 * (1 - factor * 0.6))
        g = int(25 * (1 - factor * 0.6))
        b = int(45 * (1 - factor * 0.5))
        ImageDraw.Draw(base_layer).line([(0, y), (size, y)], fill=(r, g, b, 255))
    
    img.paste(base_layer, (0, 0), base_mask)

    # Gradient border ring (Electric cyan #00F0FF to Sapphire #2563EB)
    ring_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(ring_img)
    ring_thickness = 10
    ring_draw.ellipse(
        [center - radius + 2, center - radius + 2, center + radius - 2, center + radius - 2],
        outline=(0, 210, 255, 220),
        width=ring_thickness,
    )
    # Add inner softer ring
    ring_draw.ellipse(
        [center - radius + 14, center - radius + 14, center + radius - 14, center + radius - 14],
        outline=(59, 130, 246, 120),
        width=3,
    )
    img.alpha_composite(ring_img)

    # Central Motif: Futuristic AI Neural Core / Faceted Prism
    # 1. Subtle background grid or orbital arcs
    arcs_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    arcs_draw = ImageDraw.Draw(arcs_img)
    # Tilted orbital ring
    orbital_box = [center - radius * 0.65, center - radius * 0.25, center + radius * 0.65, center + radius * 0.25]
    arcs_draw.ellipse(orbital_box, outline=(147, 197, 253, 90), width=4)
    arcs_img = arcs_img.rotate(35, center=(center, center), resample=Image.BICUBIC)
    img.alpha_composite(arcs_img)

    # 2. Central Core: Glowing faceted diamond / prism monogram
    core_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    core_draw = ImageDraw.Draw(core_img)

    top_pt = (center, center - 110)
    bottom_pt = (center, center + 110)
    left_pt = (center - 95, center)
    right_pt = (center + 95, center)
    inner_top = (center, center - 45)
    inner_bottom = (center, center + 45)

    # Facet 1: Top-Left (bright electric cyan #38BDF8)
    core_draw.polygon([top_pt, left_pt, (center, center)], fill=(56, 189, 248, 230))
    # Facet 2: Top-Right (pure bright cyan/white highlight #7DD3FC)
    core_draw.polygon([top_pt, right_pt, (center, center)], fill=(125, 211, 252, 255))
    # Facet 3: Bottom-Left (deep azure #0284C7)
    core_draw.polygon([bottom_pt, left_pt, (center, center)], fill=(2, 132, 199, 210))
    # Facet 4: Bottom-Right (deep cobalt #1D4ED8)
    core_draw.polygon([bottom_pt, right_pt, (center, center)], fill=(29, 78, 216, 240))

    # Inner core crystal / spark (White-cyan glow)
    spark_pts = [
        (center, center - 40),
        (center + 20, center),
        (center, center + 40),
        (center - 20, center),
    ]
    core_draw.polygon(spark_pts, fill=(240, 249, 255, 255))

    # Outline accents
    core_draw.line([top_pt, right_pt, bottom_pt, left_pt, top_pt], fill=(255, 255, 255, 240), width=3)
    core_draw.line([top_pt, bottom_pt], fill=(255, 255, 255, 180), width=2)
    core_draw.line([left_pt, right_pt], fill=(255, 255, 255, 180), width=2)

    img.alpha_composite(core_img)

    # Add 4 neural node satellites connected by thin glowing lines
    sat_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sat_draw = ImageDraw.Draw(sat_img)
    node_coords = [
        (center - 130, center - 75),
        (center + 130, center - 75),
        (center - 130, center + 75),
        (center + 130, center + 75),
    ]
    node_radius = 8
    for nx, ny in node_coords:
        # Connecting line
        sat_draw.line([(nx, ny), (center, center)], fill=(96, 165, 250, 70), width=2)
        # Node glow
        sat_draw.ellipse([nx - node_radius - 4, ny - node_radius - 4, nx + node_radius + 4, ny + node_radius + 4], fill=(0, 210, 255, 100))
        # Node core
        sat_draw.ellipse([nx - node_radius, ny - node_radius, nx + node_radius, ny + node_radius], fill=(224, 242, 254, 255))

    img.alpha_composite(sat_img)

    return img

def main():
    resources_dir = Path("frontend/electron/resources")
    resources_dir.mkdir(parents=True, exist_ok=True)

    icon_img = create_personal_ai_icon()

    # Save PNG
    png_path = resources_dir / "icon.png"
    icon_img.save(png_path, format="PNG")
    print(f"Saved {png_path} ({png_path.stat().st_size} bytes)")

    # Save multi-size ICO
    ico_path = resources_dir / "icon.ico"
    # Windows icon sizes: 256, 128, 64, 48, 32, 16
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icon_img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Saved {ico_path} ({ico_path.stat().st_size} bytes)")

    # Also update placeholder_icon.ico so old references get the high-quality multi-size icon as well
    placeholder_path = resources_dir / "placeholder_icon.ico"
    icon_img.save(placeholder_path, format="ICO", sizes=sizes)
    print(f"Updated {placeholder_path} ({placeholder_path.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
