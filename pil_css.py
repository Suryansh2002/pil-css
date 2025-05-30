from __future__ import annotations

from io import BytesIO
from typing import Literal

from PIL import Image, ImageDraw, ImageFont, ImageColor

Ink = ImageDraw._Ink # type: ignore


class FlexBox:
    def __init__(
        self,
        image: Image.Image,
        *,
        padding: int = 0,
        gap: int = 0,
        direction: Literal["row", "column"] = "row",
        justify: Literal[
            "start", "end", "center", "space-between", "space-around", "space-evenly"
        ] = "start",
        align_items: Literal["start", "end", "center"] = "start",
        flex_wrap: Literal["nowrap", "wrap"] = "wrap",
        allow_resize: bool = True,
    ) -> None:
        self.image = image
        self.size = self.image.size
        self.width, self.height = self.size

        self.items: list[Image.Image | FlexBox] = []
        self.padding = padding
        self.gap = gap

        self.direction = direction
        self.justify = justify
        self.align_items = align_items
        self.flex_wrap = flex_wrap
        self.allow_resize = allow_resize

        self._rendered = False

    def add_items(self, *image: Image.Image | FlexBox):
        if self._rendered:
            raise ValueError("Cannot add items after rendering")
        self.items.extend(image)
        return self

    def render(self) -> Image.Image:
        if self._rendered:
            return self.image

        if not self.items:
            return self.image

        lines: list[list[Image.Image]] = []
        current_line: list[Image.Image] = []
        rendered_items: list[Image.Image] = []

        for item in self.items:
            if isinstance(item, FlexBox):
                rendered_items.append(item.render())
            else:
                rendered_items.append(item)

        current_main = 0
        container_main = self.width if self.direction == "row" else self.height # type: ignore

        # === STEP 1: Line Breaking for wrapping ===
        for item in rendered_items:
            item_main = item.width if self.direction == "row" else item.height
            required_space = item_main + (self.gap if current_line else 0)
            if (
                self.flex_wrap == "wrap"
                and current_main + required_space > container_main - 2 * self.padding
            ):
                lines.append(current_line)
                current_line = [item]
                current_main = item_main
            else:
                current_line.append(item)
                current_main += required_space

        if current_line:
            lines.append(current_line)

        total_max = sum(
            max(item.height if self.direction == "row" else item.width for item in line)
            + self.gap
            for line in lines
        )
        if total_max > self.height:
            self.image = add_padding(
                self.image,
                total_max
                - (self.height if self.direction == "row" else self.width)
                + self.padding * 2,
                type=("bottom" if self.direction == "row" else "right"),
            )
            self.width, self.height = self.image.size

        alignment_offset = (
            self.height if self.direction == "row" else self.width
        ) - total_max

        # === STEP 2: Render all lines ===
        cross_cursor = self.padding
        for _, line in enumerate(lines):
            max_cross = max(
                item.height if self.direction == "row" else item.width for item in line
            )

            # Total space used by items
            total_main_size = sum(
                item.width if self.direction == "row" else item.height for item in line
            )
            num_items = len(line)
            total_gap_space = (
                (self.width if self.direction == "row" else self.height)
                - 2 * self.padding
                - total_main_size
            )

            if self.justify == "start":
                main_cursor = self.padding
                gap = self.gap
            elif self.justify == "end":
                main_cursor = (
                    (self.width if self.direction == "row" else self.height)
                    - self.padding
                    - total_main_size
                    - self.gap * (num_items - 1)
                )
                gap = self.gap
            elif self.justify == "center":
                main_cursor = (
                    self.padding + (total_gap_space - self.gap * (num_items - 1)) // 2
                )
                gap = self.gap
            elif self.justify == "space-between" and num_items > 1:
                gap = total_gap_space // (num_items - 1)
                main_cursor = self.padding
            elif self.justify == "space-around":
                gap = total_gap_space // num_items
                main_cursor = self.padding + gap // 2
            elif self.justify == "space-evenly":
                gap = total_gap_space // (num_items + 1)
                main_cursor = self.padding + gap
            else:
                main_cursor = self.padding
                gap = self.gap

            for item in line:
                if self.direction == "row":
                    if self.align_items == "center":
                        cross = (
                            cross_cursor
                            + (alignment_offset + (max_cross - item.height)) // 2
                        )
                    elif self.align_items == "end":
                        cross = cross_cursor + (
                            alignment_offset + (max_cross - item.height)
                        )
                    else:
                        cross = cross_cursor
                    self.image.paste(item, (main_cursor, cross), item)
                    main_cursor += item.width + gap
                else:
                    if self.align_items == "center":
                        cross = (
                            cross_cursor
                            + (alignment_offset + (max_cross - item.width)) // 2
                        )
                    elif self.align_items == "end":
                        cross = cross_cursor + (
                            alignment_offset + (max_cross - item.width)
                        )
                    else:
                        cross = cross_cursor
                    self.image.paste(item, (cross, main_cursor), item)
                    main_cursor += item.height + gap

            cross_cursor += max_cross + self.gap

        self._rendered = True
        return self.image

    def get_rendered_bytes(self):
        self.render()
        buffer = BytesIO()
        self.image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()


def add_padding(
    image: Image.Image,
    padding: int,
    type: Literal["all", "left", "right", "top", "bottom", "x", "y"] = "all",
) -> Image.Image:
    if type == "all":
        new_size = (image.width + 2 * padding, image.height + 2 * padding)
        new_image = Image.new("RGBA", new_size, (0, 0, 0, 0))
        new_image.paste(image, (padding, padding), image)
    elif type == "left":
        new_size = (image.width + padding, image.height)
        new_image = Image.new("RGBA", new_size, (0, 0, 0, 0))
        new_image.paste(image, (padding, 0), image)
    elif type == "right":
        new_size = (image.width + padding, image.height)
        new_image = Image.new("RGBA", new_size, (0, 0, 0, 0))
        new_image.paste(image, (0, 0), image)
    elif type == "top":
        new_size = (image.width, image.height + padding)
        new_image = Image.new("RGBA", new_size, (0, 0, 0, 0))
        new_image.paste(image, (0, padding), image)
    elif type == "bottom":
        new_size = (image.width, image.height + padding)
        new_image = Image.new("RGBA", new_size, (0, 0, 0, 0))
        new_image.paste(image, (0, 0), image)
    elif type == "x":
        new_size = (image.width + padding * 2, image.height)
        new_image = Image.new("RGBA", new_size, (255, 255, 255, 255))
        new_image.paste(image, (padding, 0), image)
    elif type == "y":
        new_size = (image.width, image.height + padding * 2)
        new_image = Image.new("RGBA", new_size, (255, 255, 255, 255))
        new_image.paste(image, (0, padding), image)
    else:
        raise ValueError(f"Invalid type: {type}")

    return new_image


def add_border(
    image: Image.Image, *, thickness: int, color: Ink = (0, 0, 0, 0)
) -> Image.Image:
    new_size = (image.width + 2 * thickness, image.height + 2 * thickness)
    new_image = Image.new("RGBA", new_size, color)
    new_image.paste(image, (thickness, thickness))
    return new_image


def text_image(
    text: str,
    *,
    size: int,
    font: str = "arial.ttf",
    fill: Ink = "white",
    background: Ink = (0, 0, 0, 0),
) -> Image.Image:
    image = Image.new("RGBA", (size, size), background)
    draw = ImageDraw.Draw(image)
    pil_font = ImageFont.truetype(font, size * 0.9)
    text_bbox = draw.textbbox((0, 0), text, font=pil_font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    if text_width > image.size[0]:
        image = image.resize((int(text_width), image.size[1])) # type: ignore
        draw = ImageDraw.Draw(image)

    text_x = (image.size[0] - text_width) // 2 - image.size[1] // 20
    text_y = (image.size[1] - text_height) // 2 - (text_height // 4)
    draw.text((text_x, text_y), text, fill=fill, font=pil_font)
    return image


def add_rounded_corners(image: Image.Image, radius: int):
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius, fill=255)
    image.putalpha(mask)
    return image


def resize_and_center_crop(
    image_path: str, target_width: int | float, target_height: int | float
):
    target_width = int(target_width)
    target_height = int(target_height)
    img = Image.open(image_path)

    orig_width, orig_height = img.size

    scale_factor = max(target_width / orig_width, target_height / orig_height)

    new_size = (int(orig_width * scale_factor), int(orig_height * scale_factor))
    img_resized = img.resize(new_size, Image.Resampling.LANCZOS) # type: ignore

    left = (new_size[0] - target_width) // 2
    top = (new_size[1] - target_height) // 2
    right = left + target_width
    bottom = top + target_height

    img_cropped = img_resized.crop((left, top, right, bottom))

    return img_cropped


def paste_on_blank_backgrond(image_path: str, target_width: int, target_height: int):
    img = Image.open(image_path)
    img_with_bg = Image.new("RGBA", (target_width, target_height), (255, 255, 255, 0))

    scale_factor = min(target_width / img.width, target_height / img.height)

    new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
    img_resized = img.resize(new_size, Image.Resampling.LANCZOS) # type: ignore

    left = (target_width - new_size[0]) // 2
    top = (target_height - new_size[1]) // 2
    img_with_bg.paste(img_resized, (left, top), img_resized)

    buff = BytesIO()
    img_with_bg.save(buff, format="PNG")
    return buff.getvalue()


def change_background(image: Image.Image, background: Ink, alpha: int = 180):
    if isinstance(background, str):
        background = ImageColor.getcolor(background, "RGBA")

        if isinstance(background, tuple):
            if len(background) == 3:
                background = background + (alpha,)
            else:
                background = background[:3] + (alpha,)

    new_image = Image.new("RGBA", image.size, background)
    new_image.paste(image, (0, 0), image)
    return new_image


def position_relative(
    base: Image.Image,
    image: Image.Image, *,
    top: int|None = None,
    bottom: int|None = None,
    left: int|None = None,
    right: int|None = None,
):
    if top and bottom:
        raise ValueError("Cannot set both top and bottom")
    if left and right:
        raise ValueError("Cannot set both left and right")
    
    if top is None and bottom is None:
        top = 0
    if left is None and right is None:
        left = 0

    if bottom is not None:
        top = base.height - bottom - image.height
    if right is not None:
        left = base.width - right - image.width

    assert top is not None, "Top must be set"
    assert left is not None, "Left must be set" 

    base.paste(image, (left, top), image)
    return base