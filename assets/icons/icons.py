#!/usr/bin/env python3

import cairosvg
import codecs
import discord
import inspect
import pathlib
import PIL
import tempfile

# I need a list of all colors that the Discord library offers, and I can't seem
# to find a good one, so I'm going to just create one here
colors = ['ash_embed', 'ash_theme', 'blue', 'blurple', 'brand_green',
    'brand_red', 'dark_blue', 'dark_embed', 'dark_gold', 'dark_gray',
    'dark_green', 'dark_grey', 'dark_magenta', 'dark_orange', 'dark_purple',
    'dark_red', 'dark_teal', 'dark_theme', 'darker_gray', 'darker_grey',
    'default', 'fuchsia', 'gold', 'green', 'greyple', 'light_embed',
    'light_gray', 'light_grey', 'light_theme', 'lighter_gray',
    'lighter_grey', 'magenta', 'og_blurple', 'onyx_embed', 'onyx_theme',
    'orange', 'pink', 'purple', 'red', 'teal', 'yellow']

def generate_pngs(svg_path: pathlib.Path, png_path: pathlib.Path):
    """Generate icons for embed messages.

    This method takes SVG files, changes their colors, and converts them into
    PNG files for use in Discord message embeds. Since uploading the image
    itself to the Discord message isn't an option, we are going to create a
    designated directory for the icons, and use the public URL for it to point
    Discord to the proper icon.

    Params:
        svg_path (pathlib.Path): The path to the SVG files to be converted.
        png_path (pathlib.Path): The path to store the resultant PNG files.
    """
    # Convert to each Discord color
    for color_name in colors:
        color_dir = png_path / color_name
        color_dir.mkdir(parents=True, exist_ok=True)
        color_hex = str(getattr(discord.Colour, color_name)())

        # Open each SVG in the directory
        for svg_file in svg_path.glob("*.svg"):
            with codecs.open(svg_file, "r", encoding="utf-8") as f:
                svg_data = f.read()

            # Convert the SVG elements to the correct new color
            svg_data = svg_data.replace("#000000", color_hex)

            # If we just save the new PNG, the icon will completely fill the
            # image, but we're going to use it in areas of Discord messages
            # where they are rendered in circles, so we're going to add margins
            # on each side so that the icon doesn't get cut off
            with tempfile.NamedTemporaryFile(delete=True) as temp:
                cairosvg.svg2png(
                    bytestring=svg_data.encode("utf-8"), write_to=temp.name)
                # Resize to add border
                img = PIL.Image.open(temp.name).convert("RGBA")
                img = PIL.ImageOps.expand(img, border=100, fill=(0, 0, 0, 0))
                img.resize((300, 300), PIL.Image.LANCZOS)

            # Save to actual PNG file
            img.save(color_dir / f"{svg_file.stem}.png", format="PNG")
            print("new file:", color_dir / f"{svg_file.stem}.png")