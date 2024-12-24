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

class ZoomableStaticBitmap(wx.StaticBitmap):
    def __init__(self, parent, id=wx.ID_ANY, bitmap=wx.NullBitmap, *args, **kwargs):
        super().__init__(parent, id, bitmap, *args, **kwargs)
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.original_bitmap = None
        self.source_pil_image = None  # Store the source PIL image
        
        # Bind mouse wheel event
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        
    def OnMouseWheel(self, event):
        if event.ControlDown():  # Only zoom if Ctrl is pressed
            # Get the rotation direction
            if wx.Platform == "__WXMAC__":
                delta = event.GetWheelRotation()
            else:
                delta = event.GetWheelRotation() / 120
            
            # Calculate new zoom level
            zoom_factor = 1.1 if delta > 0 else 0.9
            new_zoom = self.zoom_level * zoom_factor
            
            # Clamp zoom level
            new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
            
            if new_zoom != self.zoom_level:
                self.zoom_level = new_zoom
                self.UpdateZoom()
            
        event.Skip()
        
    def SetBitmap(self, bitmap, pil_image=None):
        self.original_bitmap = bitmap
        if pil_image is not None:
            self.source_pil_image = pil_image.copy()  # Store a copy of the source PIL image
        self.zoom_level = 1.0
        self.UpdateZoom()
        
    def UpdateZoom(self):
        if self.source_pil_image:  # If we have a source PIL image, use it for high-quality scaling
            try:
                # Calculate new size from original image dimensions
                orig_width, orig_height = self.source_pil_image.size
                new_width = int(orig_width * self.zoom_level)
                new_height = int(orig_height * self.zoom_level)
                
                # Resize from original PIL image
                resized_image = self.source_pil_image.copy()
                resized_image.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert PIL image to wx.Bitmap
                width, height = resized_image.size
                if resized_image.mode == 'RGBA':
                    # Create wx.Image with alpha channel
                    wx_image = wx.Image(width, height)
                    wx_image.SetData(resized_image.convert("RGB").tobytes())
                    wx_image.SetAlpha(resized_image.getchannel('A').tobytes())
                else:
                    # For RGB images
                    wx_image = wx.Image(width, height)
                    wx_image.SetData(resized_image.convert("RGB").tobytes())
                
                self.current_bitmap = wx.Bitmap(wx_image)
                
                # Update display
                super().SetBitmap(self.current_bitmap)
                
                # Adjust parent sizer if needed
                self.GetParent().Layout()
                
            except Exception as e:
                print(f"Error updating zoom: {str(e)}")
        elif self.original_bitmap:  # Fallback to bitmap scaling if no source image
            try:
                # Get original size
                orig_width = self.original_bitmap.GetWidth()
                orig_height = self.original_bitmap.GetHeight()
                
                # Calculate new size
                new_width = int(orig_width * self.zoom_level)
                new_height = int(orig_height * self.zoom_level)
                
                # Create scaled image
                img = self.original_bitmap.ConvertToImage()
                img = img.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
                self.current_bitmap = wx.Bitmap(img)
                
                # Update display
                super().SetBitmap(self.current_bitmap)
                
                # Adjust parent sizer if needed
                self.GetParent().Layout()
            except Exception as e:
                print(f"Error updating zoom: {str(e)}")

class PasteEnabledStaticBitmap(ZoomableStaticBitmap):
    def __init__(self, parent, id=wx.ID_ANY, bitmap=wx.NullBitmap, *args, **kwargs):
        super().__init__(parent, id, bitmap, *args, **kwargs)
        self.SetDropTarget(ImageDropTarget(self))
        
        # Enable paste events
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        
        # Store reference to parent frame
        self.parent_frame = self.GetTopLevelParent()
        
    def OnRightDown(self, event):
        menu = wx.Menu()
        menu.Append(wx.ID_PASTE, "Paste")
        self.PopupMenu(menu)
        menu.Destroy()
        
    def OnPaste(self, event):
        if wx.TheClipboard.Open():
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                data = wx.BitmapDataObject()
                success = wx.TheClipboard.GetData(data)
                wx.TheClipboard.Close()
                
                if success:
                    bitmap = data.GetBitmap()
                    # Convert wx.Bitmap to PIL Image
                    width, height = bitmap.GetWidth(), bitmap.GetHeight()
                    buffer = bitmap.ConvertToImage().GetData()
                    pil_image = Image.frombytes("RGB", (width, height), buffer)
                    
                    # Update the parent frame's original image and display
                    self.parent_frame.original_image = pil_image
                    self.parent_frame.display_image(self.parent_frame.left_canvas, pil_image)
                    self.parent_frame.remove_button.Enable()

class ImageDropTarget(wx.DropTarget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.data = wx.DataObjectComposite()
        self.bitmap = wx.BitmapDataObject()
        self.file = wx.FileDataObject()
        self.data.Add(self.bitmap)
        self.data.Add(self.file)
        self.SetDataObject(self.data)

    def OnDrop(self, x, y):
        return True

    def OnData(self, x, y, defResult):
        if self.GetData():
            format = self.data.GetReceivedFormat()
            if format.GetType() == wx.DF_BITMAP:
                bitmap = self.bitmap.GetBitmap()
                # Convert wx.Bitmap to PIL Image
                width, height = bitmap.GetWidth(), bitmap.GetHeight()
                buffer = bitmap.ConvertToImage().GetData()
                pil_image = Image.frombytes("RGB", (width, height), buffer)
                
                # Update the parent frame's original image and display
                self.window.parent_frame.original_image = pil_image
                self.window.parent_frame.display_image(self.window.parent_frame.left_canvas, pil_image)
                self.window.parent_frame.remove_button.Enable()
            elif format.GetType() == wx.DF_FILENAME:
                filename = self.file.GetFilenames()[0]
                try:
                    pil_image = Image.open(filename)
                    self.window.parent_frame.original_image = pil_image
                    self.window.parent_frame.display_image(self.window.parent_frame.left_canvas, pil_image)
                    self.window.parent_frame.remove_button.Enable()
                except Exception as e:
                    wx.MessageBox(f"Error loading image: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
        return defResult

class BackgroundRemoverApp(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up the frame
        self.SetTitle("Image Background Remover")
        self.SetSize((1000, 600))

        # Layout elements
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Canvas for original and processed images - using PasteEnabledStaticBitmap for left canvas
        # Create white background panels
        left_bg = wx.Panel(panel)
        right_bg = wx.Panel(panel)
        left_bg.SetBackgroundColour(wx.WHITE)
        right_bg.SetBackgroundColour(wx.WHITE)
        
        self.left_canvas = PasteEnabledStaticBitmap(left_bg, size=(400, 400), bitmap=wx.NullBitmap)
        self.right_canvas = ZoomableStaticBitmap(right_bg, size=(400, 400), bitmap=wx.NullBitmap)
        
        # Add canvases to their background panels
        left_bg_sizer = wx.BoxSizer(wx.VERTICAL)
        right_bg_sizer = wx.BoxSizer(wx.VERTICAL)
        left_bg_sizer.Add(self.left_canvas, 1, wx.EXPAND)
        right_bg_sizer.Add(self.right_canvas, 1, wx.EXPAND)
        left_bg.SetSizer(left_bg_sizer)
        right_bg.SetSizer(right_bg_sizer)

        # Side-by-side canvas layout
        canvas_sizer = wx.BoxSizer(wx.HORIZONTAL)
        canvas_sizer.Add(left_bg, 1, wx.ALL | wx.EXPAND, 10)
        canvas_sizer.Add(right_bg, 1, wx.ALL | wx.EXPAND, 10)

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

        # Add keyboard shortcut for paste
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('V'), wx.ID_PASTE)
        ])
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.on_paste, id=wx.ID_PASTE)

        # Placeholder for images
        self.original_image = None
        self.processed_image = None

    def on_paste(self, event):
        # Forward paste event to left canvas
        paste_event = wx.CommandEvent(wx.EVT_MENU.typeId, wx.ID_PASTE)
        self.left_canvas.ProcessEvent(paste_event)

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
        # Reset zoom level when setting new image
        canvas.zoom_level = 1.0
        canvas.SetBitmap(wx_image, pil_image)


if __name__ == "__main__":
    app = wx.App(False)
    frame = BackgroundRemoverApp(None)
    frame.Show()
    app.MainLoop()