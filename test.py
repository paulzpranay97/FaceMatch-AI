# import requests

# url = "http://127.0.0.1:5000/match"
# file_path = "C:/Users/Avrajyoti Hovsol/Desktop/face_match/face_match_api/test_image/image3.png"

# # Open the image file in binary mode
# with open(file_path, "rb") as image_file:
#     files = {"image": image_file}
#     response = requests.post(url, files=files)

# # Print the response
# print("Status Code:", response.status_code)
# print("Response JSON:", response.json())

import requests

# API endpoint
url = "http://127.0.0.1:5000/add_to_gallery"

# Headers
headers = {
    "app-id": "test_app_id",  # Replace with a valid `app_id` from your database
    "app-key": "test_app_key"  # Replace with a valid `app_key` from your database
}

# Image file to upload
file_path = "C:/Users/Avrajyoti Hovsol/Downloads/IMG_20221001_123801.jpg"  # Replace with the path to your test image

# Prepare the file for upload
files = {"image": open(file_path, "rb")}

# Send the POST request
try:
    response = requests.post(url, headers=headers, files=files)

    # Print the response
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

except Exception as e:
    print(f"An error occurred: {e}")
