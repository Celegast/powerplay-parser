"""
Example usage of PowerplayOCR class
"""

from powerplay_ocr import PowerplayOCR
import os


def example_process_single_image():
    """Example: Process a single screenshot"""
    print("Example 1: Process single image")
    print("-" * 40)

    ocr = PowerplayOCR()

    # Replace with your actual screenshot path
    image_path = "path/to/your/screenshot.png"

    if os.path.exists(image_path):
        info = ocr.process_screenshot(image_path)
        print("\nExtracted Information:")
        print(f"Systems: {info['systems']}")
        print(f"Distances: {info['distances']}")
        print(f"Allegiances: {info['allegiances']}")
    else:
        print(f"Image not found: {image_path}")


def example_batch_process():
    """Example: Process multiple screenshots from a directory"""
    print("\nExample 2: Batch process screenshots")
    print("-" * 40)

    ocr = PowerplayOCR()

    # Process all PNG files in screenshots directory
    screenshots_dir = "screenshots"

    if os.path.exists(screenshots_dir):
        image_files = [f for f in os.listdir(screenshots_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]

        print(f"Found {len(image_files)} images")

        for image_file in image_files:
            image_path = os.path.join(screenshots_dir, image_file)
            print(f"\nProcessing: {image_file}")
            ocr.process_screenshot(image_path)
    else:
        print(f"Directory not found: {screenshots_dir}")


def example_custom_region():
    """Example: Capture specific screen region"""
    print("\nExample 3: Capture custom screen region")
    print("-" * 40)

    ocr = PowerplayOCR()

    # Define region (x, y, width, height)
    # Example: Capture top-left quarter of screen
    region = (0, 0, 960, 540)

    print("Taking screenshot of custom region in 3 seconds...")
    import time
    time.sleep(3)

    screenshot_path = ocr.take_screenshot(region=region)
    info = ocr.process_screenshot(screenshot_path)

    print("\nCaptured and processed custom region")


def example_with_custom_tesseract_path():
    """Example: Using custom Tesseract path"""
    print("\nExample 4: Custom Tesseract path")
    print("-" * 40)

    # Specify custom Tesseract path (Windows example)
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    ocr = PowerplayOCR(tesseract_path=tesseract_path)

    print(f"Initialized with Tesseract path: {tesseract_path}")


if __name__ == "__main__":
    print("=" * 50)
    print("PowerplayOCR - Example Usage")
    print("=" * 50)

    # Uncomment the examples you want to run:

    # example_process_single_image()
    # example_batch_process()
    # example_custom_region()
    # example_with_custom_tesseract_path()

    print("\nUncomment the examples in example_usage.py to run them")
