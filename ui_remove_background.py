import wx
from PIL import Image
import rembg
from io import BytesIO
import os
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
class BackgroundRemoverApp(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up the frame
        self.SetTitle("Image Background Remover")
        self.SetSize((1000, 600))

        # Layout elements
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Canvas for original and processed images
        self.left_canvas = wx.StaticBitmap(panel, size=(400, 400))
        self.right_canvas = wx.StaticBitmap(panel, size=(400, 400))

        # Side-by-side canvas layout
        canvas_sizer = wx.BoxSizer(wx.HORIZONTAL)
        canvas_sizer.Add(self.left_canvas, 1, wx.ALL | wx.EXPAND, 10)
        canvas_sizer.Add(self.right_canvas, 1, wx.ALL | wx.EXPAND, 10)

        # Buttons to load image and remove background
        self.load_button = wx.Button(panel, label="Load Image")
        self.load_button.Bind(wx.EVT_BUTTON, self.on_load_image)

        self.remove_button = wx.Button(panel, label="Remove Background")
        self.remove_button.Bind(wx.EVT_BUTTON, self.on_remove_background)
        self.remove_button.Disable()  # Initially disabled until image is loaded

        # Button layout
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.load_button, 0, wx.ALL, 10)
        button_sizer.Add(self.remove_button, 0, wx.ALL, 10)

        # Add canvases and buttons to main sizer
        sizer.Add(canvas_sizer, 1, wx.EXPAND)
        sizer.Add(button_sizer, 0, wx.CENTER)

        # Set the sizer for the panel
        panel.SetSizer(sizer)
        self.Center()

        # Placeholder for images
        self.original_image = None
        self.processed_image = None

    def on_load_image(self, event):
        """Handles the image loading process."""
        # Open a file dialog to select an image
        with wx.FileDialog(
            self, "Open Image", wildcard="Image files (*.jpg;*.png)|*.jpg;*.png",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return  # Cancelled

            # Load selected image
            input_path = file_dialog.GetPath()
            self.original_image = Image.open(input_path)

            # Display the original image in the left canvas
            self.display_image(self.left_canvas, self.original_image)

            # Enable the "Remove Background" button
            self.remove_button.Enable()

    def on_remove_background(self, event):
        """Handles the background removal process."""
        if not self.original_image:
            wx.MessageBox("Please load an image first.", "Error", wx.OK | wx.ICON_ERROR)
            return

        try:
            # Initialize rembg session with CPU provider if CUDA is not available
            import torch
            
            # Print CUDA availability
            print(f"CUDA Available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                print(f"CUDA Device Name: {torch.cuda.get_device_name(0)}")
                
            # Configure providers based on device availability
            providers = []
            if torch.cuda.is_available():
                providers = ['CUDAExecutionProvider']
            else:
                providers = ['CPUExecutionProvider']
                
            print(f"Using providers: {providers}")
                    
            # Create rembg session with specific providers
            rembg_session = rembg.new_session(providers=providers)
            
            # Process the image
            resized_image = resize_image_with_aspect_ratio(self.original_image, (1280, 1280))
            processed_image = remove_background(resized_image, rembg_session)
            
            # Display the processed image
            self.processed_image = processed_image
            self.display_image(self.right_canvas, self.processed_image)
            
            # Save the image
            save_final_image(processed_image, "output.png")
                
        except Exception as e:
            print(f"Error details: {str(e)}")  # Print error to console for debugging
            wx.MessageBox(f"Error processing image: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)

    def display_image(self, canvas, pil_image):
        """Displays a PIL image on a wx.StaticBitmap canvas."""
        # Resize the image for the canvas while maintaining aspect ratio
        image = pil_image.copy()
        image.thumbnail((400, 400), Image.Resampling.LANCZOS)

        # Handle RGBA images properly
        if image.mode == 'RGBA':
            # Create wx.Image with alpha channel
            wx_image = wx.Image(*image.size)
            wx_image.SetData(image.convert("RGB").tobytes())
            wx_image.SetAlpha(image.getchannel('A').tobytes())
        else:
            # For RGB images
            wx_image = wx.Image(*image.size)
            wx_image.SetData(image.convert("RGB").tobytes())

        # Convert to bitmap and display
        wx_image = wx_image.ConvertToBitmap()
        canvas.SetBitmap(wx_image)


if __name__ == "__main__":
    app = wx.App(False)
    frame = BackgroundRemoverApp(None)
    frame.Show()
    app.MainLoop()
