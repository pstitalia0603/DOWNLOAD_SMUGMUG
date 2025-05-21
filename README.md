# Download your Smugmug photos from the API!

## 🔐 Replace with your credentials

- API DOCUMENTATION: https://api.smugmug.com/api/v2/doc/tutorial/basics.html
- https://api.smugmug.com/api/v2/doc
- FIND API INFO: https://www.smugmug.com/app/developer

## 📸 SmugMug Photo Downloader

A Python script to authenticate with the SmugMug API via OAuth 1.0a, retrieve all albums and images for a user, and download the images organized by album folder.

## 🚀 Features

- OAuth 1.0a authentication flow with manual PIN entry
- Fetches user info (nickname, user key, etc.)
- Retrieves all albums (auto-paginated)
- Retrieves all images within each album (auto-paginated)

📁 Folder Structure
All images are downloaded to a local folder called smugmug_photos, which is automatically created in the same directory as the script. Inside that folder, each album is saved in its own subfolder named after the album title.

Example layout:

```
your_project_directory/
├── download_smugmug_photos.py
├── smugmug_photos/
│ ├── Summer Vacation 2023/
│ │ ├── IMG_001.jpg
│ │ ├── IMG_002.jpg
│ │ └── ...
│ ├── Family Reunion/
│ │ ├── photo1.jpg
│ │ ├── photo2.jpg
│ │ └── ...
│ └── ...
```

- Handles SmugMug API rate limits (429) and respects Retry-After headers
- Logs remaining requests and reset times via rate limit headers

## 🛠️ Requirements

- Python 3.7+
- `requests`
- `requests_oauthlib`

Install requirements:

```bash
pip install requests requests_oauthlib
```

## 🔐 Configuration

Update your script with your SmugMug API credentials:

- API_KEY = "YOUR_API_KEY"
- API_SECRET = "YOUR_API_SECRET"

## 🧪 Usage

Run the script:

```python
python download_smugmug_photos.py
```

You'll be prompted to visit a SmugMug authorization URL and enter a PIN.

Once authenticated, the script will:

Fetch your SmugMug albums

Fetch all images from each album

Download images into a folder named smugmug_photos

## 🧠 Notes

SmugMug paginates API responses; this script handles pagination automatically.

SmugMug imposes a rate limit on API usage. If you hit the limit (status code 429), the script will pause and retry automatically.

Album names are sanitized for safe folder creation.

Duplicate images will not be re-downloaded if they already exist locally.

## 📝 To-Do

Add support for incremental syncing (skip albums that haven’t changed)

Add progress bar

Add logging or summary report

## 📄 License

MIT License. Use freely and modify as needed.
