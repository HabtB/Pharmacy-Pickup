import os
import shutil
import re

# PWD is python_server
base_dir = os.path.dirname(os.path.abspath(__file__))
images_dir = os.path.join(base_dir, '..', 'Images')
assets_dir = os.path.join(base_dir, '..', 'assets', 'images')

def sanitize_filename(name):
    """
    Convert 'Main Pharmacy - Zone Y-i.jpeg' to 'main_pharmacy_zone_y_i.jpeg'
    """
    # Remove extension first
    name_no_ext, ext = os.path.splitext(name)
    
    # Lowercase
    s = name_no_ext.lower()
    
    # Replace spaces and dashes with underscores
    s = re.sub(r'[\s-]+', '_', s)
    
    # Fix parentheses
    s = s.replace('(', '').replace(')', '')
    
    # Clean up double underscores
    s = re.sub(r'_+', '_', s)
    
    return s.strip('_') + ext.lower()

def organize_images():
    if not os.path.exists(images_dir):
        print(f"Error: Images directory not found at {images_dir}")
        return

    print(f"Processing images in {images_dir}")
    
    # Ensure subfolders exist in Images
    subfolders = ['Fridge', 'Main Pharmacy', 'Store']
    for sub in subfolders:
        os.makedirs(os.path.join(images_dir, sub), exist_ok=True)
        
    for filename in os.listdir(images_dir):
        if filename.startswith('.'):
             continue
        if os.path.isdir(os.path.join(images_dir, filename)):
            continue
            
        src_path = os.path.join(images_dir, filename)
        
        # Determine Category
        category = None
        if 'Fridge' in filename:
            category = 'Fridge'
        elif 'Main Pharmacy' in filename:
            category = 'Main Pharmacy'
        elif 'Store Location' in filename:
            category = 'Store'
            
        if category:
            # 1. Sync to Assets (Copy & Rename)
            new_name = sanitize_filename(filename)
            dest_asset_path = os.path.join(assets_dir, new_name)
            
            # Check if it already exists to avoid overwriting (or maybe we SHOULD overwrite?)
            # Let's overwrite to ensure we have the latest "Zone Y" etc.
            shutil.copy2(src_path, dest_asset_path)
            print(f"  [SYNC] Copied to assets/images/{new_name}")
            
            # 2. Move to Subfolder in Images (Organize source)
            # dest_source_path = os.path.join(images_dir, category, filename)
            # shutil.move(src_path, dest_source_path)
            # print(f"  [MOVE] Moved to Images/{category}/{filename}")
            
            # NOTE: For now I will NOT move them, just sync, to be safe and let the user verify first.
            # But the user Asked to organize them.
            # Okay, I will move them.
            dest_source_path = os.path.join(images_dir, category, filename)
            shutil.move(src_path, dest_source_path)
            print(f"  [MOVE] Moved to Images/{category}/{filename}")
            
        else:
            print(f"  [SKIP] Could not categorize: {filename}")

if __name__ == "__main__":
    organize_images()
