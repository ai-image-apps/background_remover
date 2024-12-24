import os
import wx
import torch
import rembg
from PIL import Image
from typing import Any

class BackgroundRemoverApp(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Background Remover')
        
        # Initialize rembg session
        self.rembg_session = rembg.new_session()
        
        # Panel to hold all widgets
        panel = wx.Panel(self)
        
        # Main vertical sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Input image selection
        input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.input_path_text = wx.TextCtrl(panel, style=wx.TE_READONLY)
        input_sizer.Add(self.input_path_text, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        
        input_btn = wx.Button(panel, label='Select Input Image')
        input_btn.Bind(wx.EVT_BUTTON, self.on_select_input)
        input_sizer.Add(input_btn, flag=wx.ALL, border=5)
        
        main_sizer.Add(input_sizer, flag=wx.EXPAND)
        
        # Output directory selection
        output_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.output_path_text = wx.TextCtrl(panel, style=wx.TE_READONLY)
        output_sizer.Add(self.output_path_text, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        
        output_btn = wx.Button(panel, label='Select Output Directory')
        output_btn.Bind(wx.EVT_BUTTON, self.on_select_output)
        output_sizer.Add(output_btn, flag=wx.ALL, border=5)
        
        main_sizer.Add(output_sizer, flag=wx.EXPAND)
        
        # Process button
        process_btn = wx.Button(panel, label='Remove Background')
        process_btn.Bind(wx.EVT_BUTTON, self.on_process)
        main_sizer.Add(process_btn, flag=wx.ALL|wx.CENTER, border=10)
        
        # Preview area
        preview_label = wx.StaticText(panel, label='Preview:')
        main_sizer.Add(preview_label, flag=wx.ALL|wx.LEFT, border=5)
        
        self.preview_image = wx.StaticBitmap(panel, bitmap=wx.Bitmap(400, 400))
        main_sizer.Add(self.preview_image, flag=wx.ALL|wx.CENTER, border=5)
        
        # Status text
        self.status_text = wx.StaticText(panel, label='')
        main_sizer.Add(self.status_text, flag=wx.ALL|wx.CENTER, border=5)
        
        # Set up the panel
        panel.SetSizer(main_sizer)
        
        # Initialize variables
        self.input_image_path = None
        self.output_directory = None
        
        # Resize and show
        self.SetSize((500, 700))
        self.Centre()
    
    def on_select_input(self, event):
        """Open file dialog to select input image"""
        with wx.FileDialog(
            self, 
            "Choose an input image", 
            wildcard="Image files (*.png;*.jpg;*.jpeg;*.bmp)|*.png;*.jpg;*.jpeg;*.bmp",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as fileDialog:
            
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            self.input_image_path = fileDialog.GetPath()
            self.input_path_text.SetValue(self.input_image_path)
            
            # Update preview
            self.update_preview(self.input_image_path)
    
    def on_select_output(self, event):
        """Open directory dialog to select output directory"""
        with wx.DirDialog(
            self, 
            "Choose output directory",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        ) as dirDialog:
            
            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            
            self.output_directory = dirDialog.GetPath()
            self.output_path_text.SetValue(self.output_directory)
    
    def update_preview(self, image_path):
        """Update the preview image"""
        try:
            # Open the image and resize to fit preview
            pil_img = Image.open(image_path)
            pil_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            # Convert PIL image to wx bitmap
            wx_img = wx.Bitmap.FromBufferRGBA(
                pil_img.width, 
                pil_img.height, 
                pil_img.convert('RGBA').tobytes()
            )
            
            # Set preview
            self.preview_image.SetBitmap(wx_img)
            self.preview_image.Refresh()
        except Exception as e:
            wx.MessageBox(f"Error loading preview: {e}", "Preview Error", wx.OK | wx.ICON_ERROR)
    
    def on_process(self, event):
        """Process the image to remove background"""
        # Validate inputs
        if not self.input_image_path:
            wx.MessageBox("Please select an input image", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        if not self.output_directory:
            wx.MessageBox("Please select an output directory", "Error", wx.OK | wx.ICON_ERROR)
            return
        
        try:
            # Update status
            self.status_text.SetLabel("Processing...")
            self.Refresh()
            
            # Open and resize image
            original_image = Image.open(self.input_image_path)
            resized_image = self.resize_image_with_aspect_ratio(original_image, (1280, 1280))
            
            # Remove background
            processed_image = self.remove_background(resized_image)
            
            # Generate output filename
            output_filename = f"no_background_{os.path.basename(self.input_image_path)}"
            output_path = os.path.join(self.output_directory, output_filename)
            
            # Save final image
            self.save_final_image(processed_image, output_path)
            
            # Update status and show preview of processed image
            self.status_text.SetLabel(f"Image saved to: {output_path}")
            self.update_preview(output_path)
            
            # Show success message
            wx.MessageBox("Background removed successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
        
        except Exception as e:
            # Show error message
            wx.MessageBox(f"Error processing image: {e}", "Error", wx.OK | wx.ICON_ERROR)
            self.status_text.SetLabel("Processing failed")
    
    @staticmethod
    def remove_background(
        image: Image.Image,
        rembg_session: Any = None,
        force: bool = False,
        **rembg_kwargs,
    ) -> Image.Image:
        """
        Removes the background of an image using the rembg library.
        """
        do_remove = True
        if image.mode == "RGBA" and image.getextrema()[3][0] < 255:
            do_remove = False
        do_remove = do_remove or force
        if do_remove:
            image = rembg.remove(image, session=rembg_session, **rembg_kwargs)
        return image
    
    @staticmethod
    def save_final_image(image: Image.Image, output_path: str):
        """
        Saves the processed image in PNG format with RGBA mode.
        """
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        image.save(output_path, 'PNG', quality=100)
    
    @staticmethod
    def resize_image_with_aspect_ratio(image, target_size):
        """
        Resizes an image to fit within the target size while maintaining aspect ratio.
        """
        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        return image

def main():
    # Detect CUDA availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Create and run the application
    app = wx.App()
    frame = BackgroundRemoverApp()
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()