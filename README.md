# Speech to Text Transcription Tool

This project is a Python script that uses Google Cloud services to transcribe audio files to text. 
Everything you have to do is to add new m4a audio file to your google drive folder then open terminal and run the python file. Your transcription is ready in 1-3 minutes in your google drive destination folder.

## How does it work

The script downloads audio files from a specified Google Drive folder, converts them to the WAV format, uploads them to a specified Google Cloud Storage bucket, transcribes them using the Google Speech-to-Text API, and uploads the resulting text files to a specified Google Drive folder.

## How to use the tool

### Prerequisites

Before using the tool, you need to set up a few things:
1. Create a new Google Cloud project (if you don't have one already) and enable the Google Drive API, Google Cloud Storage API, and Google Speech-to-Text API for the project.
2. Create a new service account for the project and download the JSON key file for the service account.
3. Share the Google Drive folder from which you want to transcribe audio files with the email address of the service account. (The email address can be found in the JSON key file.)
4. Create a new Google Cloud Storage bucket to store the converted audio files and make sure the service account has permission to access and upload files to the bucket.

### Installation

1. Clone this repository to your local machine.
2. Install the required Python packages by running pip install -r requirements.txt in your terminal.

### Usage

1. Open the transcribe.py file in a text editor.
2. Modify the following variables at the beginning of the file to match your setup:
    * SERVICE_ACCOUNT_FILE: the path to the JSON key file for the service account.
    * SOURCE_FOLDER_ID: the ID of the Google Drive folder from which you want to transcribe audio files.
    * DESTINATION_FOLDER_ID: the ID of the Google Drive folder to which you want to upload the resulting text files.
    * bucket_name: the name of the Google Cloud Storage bucket to which you want to upload the converted audio files.
3. Save the transcribe.py file.
4. Double-check that you have the correct bucket name in the bucket_name variable and that the service account JSON key has the necessary permissions to access and upload files to the Google Cloud Storage bucket.
5. Open your terminal and navigate to the directory where the transcribe.py file is located.
6. Run the command python transcribe.py to start the transcription process.

## Troubleshooting

### Permission issues

If you encounter permission issues when running the script, make sure the service account has the necessary permissions to access the Google Cloud resources, such as Google Cloud Storage or the Speech-to-Text API.

To resolve this issue you have to check both platforms: 

### 1. Google Drive
1. Open your google drive account and navigate to the SOURCE and DESTINATION folders
2. Open permission settings and add the email from your SERVICE ACCOUNT to the access list

Here is how you can find one
- Go to GCP console and navigate to the IAM & Admin page.
- Locate the service account that corresponds to the JSON key file you are using in your code. The email address of the service account is usually in the format <account-name>@<project-id>.iam.gserviceaccount.com.

### 2. GCP

1. Go to the Google Cloud Console.
2. Select your project from the top-left dropdown menu.
3. Navigate to the IAM & Admin page.
4. Locate the service account that corresponds to the JSON key file you are using in your code. The email address of the service account is usually in the format <account-name>@<project-id>.iam.gserviceaccount.com.
5. Click the pencil/edit icon next to the service account to edit its permissions.
6. Add the necessary roles to the service account. For the given code, you need the following roles:
    * roles/storage.admin (or roles/storage.objectAdmin) to access Google Cloud Storage.
    * roles/speech.admin (or roles/speech.editor) to access Speech-to-Text API.
7. Save the changes.
