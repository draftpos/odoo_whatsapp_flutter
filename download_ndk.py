import os
import sys
import urllib.request
import zipfile
import shutil
import time

url = "https://dl.google.com/android/repository/android-ndk-r28c-windows.zip"
zip_path = r"C:\Users\Ashley\AppData\Local\Android\Sdk\ndk\android-ndk-r28c-windows.zip"
extract_path = r"C:\Users\Ashley\AppData\Local\Android\Sdk\ndk"
final_path = r"C:\Users\Ashley\AppData\Local\Android\Sdk\ndk\28.2.13676358"
EXPECTED_SIZE = 748118221

def download_file_with_resume(url, dest, expected_size):
    max_retries = 30
    for attempt in range(max_retries):
        current_size = os.path.getsize(dest) if os.path.exists(dest) else 0
        if current_size == expected_size:
            print("Download already complete.")
            return True
        if current_size > expected_size:
            print("File is larger than expected. Restarting download.")
            os.remove(dest)
            current_size = 0
            
        print(f"Downloading (attempt {attempt + 1}/{max_retries})... Current size: {current_size}/{expected_size} bytes")
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        if current_size > 0:
            req.add_header('Range', f'bytes={current_size}-')
            
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(dest, 'ab' if current_size > 0 else 'wb') as out_file:
                    while True:
                        chunk = response.read(8192 * 4)
                        if not chunk:
                            break
                        out_file.write(chunk)
        except Exception as e:
            print(f"Download interrupted: {e}")
            time.sleep(2)
            continue
            
    current_size = os.path.getsize(dest) if os.path.exists(dest) else 0
    if current_size == expected_size:
        return True
    return False

def extract_file(zip_path, extract_to):
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete.")

def main():
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)
    
    if os.path.exists(final_path):
        print(f"Directory {final_path} already exists. Cleaning up...")
        shutil.rmtree(final_path)

    print("Starting robust download...")
    success = download_file_with_resume(url, zip_path, EXPECTED_SIZE)
    if not success:
        print("Failed to download fully after multiple retries.")
        sys.exit(1)

    print("Verifying zip...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            if zf.testzip() is not None:
                raise Exception("Corrupt zip inside")
        print("Zip is valid.")
    except Exception as e:
        print(f"Zip is invalid ({e}). Deleting and exiting.")
        os.remove(zip_path)
        sys.exit(1)

    extract_file(zip_path, extract_path)
    
    extracted_folder = os.path.join(extract_path, "android-ndk-r28c")
    if os.path.exists(extracted_folder):
        print(f"Renaming {extracted_folder} to {final_path}...")
        os.rename(extracted_folder, final_path)
    
    print("NDK installation complete.")

if __name__ == "__main__":
    main()
