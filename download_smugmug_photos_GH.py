import os
import requests
from requests_oauthlib import OAuth1Session
import json
import time
from datetime import datetime

# 🔐 Replace with your credentials
# API DOCUMENTATION: https://api.smugmug.com/api/v2/doc/tutorial/basics.html
# https://api.smugmug.com/api/v2/doc
# FIND API INFO: https://www.smugmug.com/app/developer
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"

# OAuth endpoints
REQUEST_TOKEN_URL = "https://api.smugmug.com/services/oauth/1.0a/getRequestToken"
AUTHORIZE_URL = "https://api.smugmug.com/services/oauth/1.0a/authorize"
ACCESS_TOKEN_URL = "https://api.smugmug.com/services/oauth/1.0a/getAccessToken"

# Where to save downloaded photos
DOWNLOAD_FOLDER = os.path.abspath("smugmug_photos")
print(f"Downloading to folder: {DOWNLOAD_FOLDER}")


def oauth_login():
    print("🔐 Starting OAuth session...")
    oauth = OAuth1Session(API_KEY, client_secret=API_SECRET, callback_uri="oob")

    try:
        fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    except Exception as e:
        print(f"❌ Failed to fetch request token: {e}")
        return None

    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")

    print("✅ Got request token.")
    auth_url = oauth.authorization_url(AUTHORIZE_URL)
    print(f"\n🔗 Visit this URL to authorize the app:\n{auth_url}")

    verifier = input("\n🔑 Enter the PIN from SmugMug: ")

    oauth = OAuth1Session(
        API_KEY,
        client_secret=API_SECRET,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )

    try:
        tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)
    except Exception as e:
        print(f"❌ Failed to fetch access token: {e}")
        return None

    print("✅ Access token obtained.")
    return OAuth1Session(
        API_KEY,
        client_secret=API_SECRET,
        resource_owner_key=tokens["oauth_token"],
        resource_owner_secret=tokens["oauth_token_secret"],
    )


def get_user_info(session):
    resp = session.get(
        "https://api.smugmug.com/api/v2!authuser",
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    user = data["Response"]["User"]
    return {
        "NickName": user["NickName"],
        "Uri": user["Uri"],  # e.g., /api/v2/user/abcd-1234-ef56
        "UserKey": user.get("UserKey"),  # optional
    }


def check_rate_limit(response):
    headers = response.headers

    remaining = headers.get("X-RateLimit-Remaining")
    reset_timestamp = headers.get("X-RateLimit-Reset")
    retry_after = headers.get("Retry-After")

    if remaining is not None:
        print(f"Rate Limit Remaining: {remaining}")

    if reset_timestamp is not None:
        reset_time = datetime.fromtimestamp(int(reset_timestamp))
        print(
            f"Rate Limit Resets At: {reset_time.strftime('%Y-%m-%d %H:%M:%S')} (local time)"
        )

    if response.status_code == 429:
        if retry_after:
            print(f"Rate limit hit! Retry after {retry_after} seconds.")
            wait_seconds = int(retry_after)
            print(f"Waiting {wait_seconds} seconds before retrying...")
            time.sleep(wait_seconds)
        else:
            print("Rate limit hit! No Retry-After header found.")
            # Default wait time if Retry-After missing
            time.sleep(60)


def get_albums(session, user_uri):
    albums = []
    url = f"https://api.smugmug.com{user_uri}!albums?count=300"
    while url:
        print(f"📥 Fetching albums: {url}")
        resp = session.get(url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        albums.extend(data["Response"].get("Album", []))
        next_page = data["Response"].get("NextPage")
        url = f"https://api.smugmug.com{next_page}" if next_page else None
    return albums


def get_images(session, album_uri):
    images = []
    url = f"https://api.smugmug.com{album_uri}!images?count=5500"
    while url:
        resp = session.get(url, headers={"Accept": "application/json"})
        check_rate_limit(resp)

        if resp.status_code == 429:
            # After waiting inside check_rate_limit, retry this iteration
            continue

        if resp.status_code == 403:
            print("❌ Access forbidden (403). Your token may be expired or invalid.")
            print("Please re-authenticate to obtain a new token.")
            # Optionally: trigger re-auth here or raise an exception
            break  # or return images so far, or raise an exception

        resp.raise_for_status()
        data = resp.json()
        images.extend(data["Response"].get("AlbumImage", []))
        next_page = data["Response"].get("NextPage")
        url = f"https://api.smugmug.com{next_page}" if next_page else None
    return images


def download_image(session, image, album_name):
    """
    Downloads a single image or video from a SmugMug album.

    This function determines whether the item is an image or a video and attempts
    to download it in the best available quality. Files are saved into a local
    folder named after the album, inside the DOWNLOAD_FOLDER.

    Args:
        session: An authenticated OAuth1 session.
        image: A dictionary representing an image or video returned by the SmugMug API.
        album_name: The name of the album this image/video belongs to.
    """
    try:
        # Get the image's original filename, or use a fallback if not present
        filename = image.get("FileName", "unknown.dat")

        # Extract the API URI to get more details about this image
        image_uri = image["Uris"]["Image"]["Uri"]
        detail_url = f"https://api.smugmug.com{image_uri}"

        # Make a request to retrieve detailed metadata for the image
        image_info = session.get(
            detail_url, headers={"Accept": "application/json"}
        ).json()

        img_data = image_info["Response"]["Image"]

        # Determine if the media is a video
        is_video = img_data.get("IsVideo", False)

        # Build the path for the album folder and create it if it doesn't exist
        album_folder = os.path.join(DOWNLOAD_FOLDER, album_name)
        os.makedirs(album_folder, exist_ok=True)

        # Construct the full file path for the downloaded file
        file_path = os.path.join(album_folder, filename)

        # Skip download if the file already exists
        if os.path.exists(file_path):
            print(f"⚠️ Already exists, skipping: {file_path}")
            return

        if is_video:
            print(f"🎥 Video detected: {filename}")

            # Try to get the URI for the highest quality video
            largest_video_uri = (
                img_data.get("Uris", {}).get("LargestVideo", {}).get("Uri")
            )
            if largest_video_uri:
                # Retrieve video metadata
                video_detail_url = f"https://api.smugmug.com{largest_video_uri}"
                video_info = session.get(
                    video_detail_url, headers={"Accept": "application/json"}
                ).json()

                # Extract the direct video URL
                video_url = video_info["Response"]["LargestVideo"].get("Url")
                if video_url:
                    # Download and save the video
                    video_response = session.get(video_url)
                    with open(file_path, "wb") as f:
                        f.write(video_response.content)
                    print(f"✅ Downloaded video: {file_path}")
                else:
                    print(f"❌ No downloadable video URL found for {filename}")
            else:
                print(f"❌ No 'LargestVideo' URI for {filename}")
        else:
            # Try to find a downloadable image URL in order of preferred quality
            image_url = (
                img_data.get("ArchivedUri") or
                img_data.get("OriginalUri") or
                img_data.get("LargestImageUrl")
            )
            if not image_url:
                print(f"❌ No downloadable image URL found for {filename}")
                return

            # Download and save the image
            img_response = session.get(image_url)
            with open(file_path, "wb") as f:
                f.write(img_response.content)
            print(f"✅ Downloaded image: {file_path}")

    except Exception as e:
        # Catch and report any errors encountered during download
        print(f"❌ Error downloading image/video {image.get('FileName')}: {e}")



def main():
    session = oauth_login()
    if not session:
        print("🔒 Authentication failed. Exiting.")
        return

    user_info = get_user_info(session)
    print(f"👋 Authenticated as: {user_info['NickName']}")

    albums = get_albums(session, user_info["Uri"])
    total_albums = len(albums)
    if total_albums == 0:
        print("No albums found.")
        return

    page_size = 15
    current_page = 0

    while True:
        start = current_page * page_size
        end = start + page_size
        page_albums = albums[start:end]

        print(
            f"\n📚 Showing albums {start + 1} to {min(end, total_albums)} of {total_albums}\n"
        )
        for i, album in enumerate(page_albums, start + 1):
            print(f"{i}. {album['Name']}")

        print(
            "\nEnter album number to download, 'n' for next page, 'p' for previous page, or 'q' to quit."
        )
        choice = input("Choice: ").strip().lower()

        if choice == "q":
            print("Exiting.")
            return
        elif choice == "n":
            if end >= total_albums:
                print("You are on the last page.")
            else:
                current_page += 1
        elif choice == "p":
            if current_page == 0:
                print("You are on the first page.")
            else:
                current_page -= 1
        elif choice.isdigit():
            choice_num = int(choice)
            if choice_num < 1 or choice_num > total_albums:
                print("Number out of range. Try again.")
            else:
                selected_album = albums[choice_num - 1]
                album_name = selected_album["Name"]
                album_uri = selected_album["Uri"]
                print(f"\n📁 Downloading album: {album_name}")
                images = get_images(session, album_uri)
                print(f"  🖼️ Found {len(images)} images")
                for image in images:
                    download_image(session, image, album_name)
                # After downloading, ask if want to continue or quit
                cont = input("\nDownload another album? (y/n): ").strip().lower()
                if cont != "y":
                    print("Exiting.")
                    return
        else:
            print("Invalid input. Please enter a number, 'n', 'p', or 'q'.")


if __name__ == "__main__":
    main()
