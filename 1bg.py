import torch
import os
from PIL import Image
import rembg
from typing import Any


def remove_background(
    image: Image.Image,
    rembg_session: Any = None,
    force: bool = False,
    **rembg_kwargs,
) -> Image.Image:
    """
    Removes the background of an image using the rembg library.

    Args:
        image (PIL.Image.Image): The input image.
        rembg_session (Any): The rembg session object.
        force (bool): Force background removal even if already transparent.
        **rembg_kwargs: Additional arguments for rembg.

    Returns:
        PIL.Image.Image: The image with the background removed.
    """
    do_remove = True
    if image.mode == "RGBA" and image.getextrema()[3][0] < 255:
        do_remove = False
    do_remove = do_remove or force
    if do_remove:
        image = rembg.remove(image, session=rembg_session, **rembg_kwargs)
    return image


def save_final_image(image: Image.Image, output_path: str):
    """
    Saves the processed image in PNG format with RGBA mode.

    Args:
        image (PIL.Image.Image): The processed image.
        output_path (str): Path to save the image.
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    image.save(output_path, 'PNG', quality=100)

def resize_image_with_aspect_ratio(image, target_size):
    """
    Resizes an image to fit within the target size while maintaining aspect ratio.

    Args:
        image (PIL.Image.Image): Input image.
        target_size (tuple): Target size as (width, height).

    Returns:
        PIL.Image.Image: Resized image.
    """
    image.thumbnail(target_size, Image.Resampling.LANCZOS)
    return image

def main():
    # Configure device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Input and output paths
    input_file_path = "girl.png"
    output_file_path = "examples/test1.png"
    os.makedirs("examples", exist_ok=True)

    # Preprocess image
    original_image = Image.open(input_file_path)
    resized_image = resize_image_with_aspect_ratio(original_image, (1280, 1280))
    resized_image.save(output_file_path)

    # Initialize rembg session
    rembg_session = rembg.new_session()

    # Process image
    processed_image = remove_background(resized_image, rembg_session)
    print('Removed')
    # Save final image
    save_final_image(processed_image, f"examples/no_background_222_{os.path.basename(input_file_path)}")
    print('Saved')


if __name__ == "__main__":
    main()
