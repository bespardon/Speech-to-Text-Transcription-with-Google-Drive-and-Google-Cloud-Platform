import os
import time
import datetime
import base64
import json
import requests
import shutil
import subprocess

from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.cloud import storage
from googleapiclient.http import MediaIoBaseDownload

from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import types

# Set up client credentials for authentication
SCOPES = ['https://www.googleapis.com/auth/drive']

# CHANGE HERE
# # Set up the path to your credentials json file 
SERVICE_ACCOUNT_FILE = 'Set up the path to your credentials json file here'
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# CHANGE HERE
# Define the ID of the source and destination folders. should something like 1tTwCA3IXpjG2iMgIGydsasdg9q7_0DCrE
# Source - where audio files are taken from
# Destination - where transcription files are uploaded to
SOURCE_FOLDER_ID = 'Set up the ID to your google drive source folder here'
DESTINATION_FOLDER_ID = 'Set up the ID to your google drive destination folder here'

# Define the MIME type of the file to be processed
MIME_TYPE = 'm4a'

# Define the file to store the IDs of the processed files
PROCESSED_FILE = 'processed_files.txt'

# CHANGE HERE
# Define input and output directories for the second code block. Choose any directory on your computer
# Directory is required to convert and store wav file
input_dir = ".../ffmpeg converter/input"
output_dir = ".../ffmpeg converter/output"

# CHANGE HERE
# Set path to service account key file. You can point same file as above. Make sure it has all permissions.
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'Set up the path to your credentials json file here'

# Define function to upload file to GCS bucket
def upload_to_gcs(file_path, bucket_name):
    # create client object
    storage_client = storage.Client()
    # get bucket object
    bucket = storage_client.bucket(bucket_name)
    # define destination filename (optional)
    destination_blob_name = os.path.basename(file_path)
    # create blob object
    blob = bucket.blob(destination_blob_name)
    # set content type to wav
    blob.content_type = "audio/wav"
    # upload file to GCS
    blob.upload_from_filename(file_path)
    # get GCS URI link
    gcs_uri = f"gs://{bucket_name}/{destination_blob_name}"
    # return GCS URI link
    return gcs_uri


# Define a function to read the IDs of the processed files from the file
def read_processed_file():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            processed_files = f.read().splitlines()
    else:
        processed_files = []
    return processed_files

# Define a function to write the IDs of the processed files to the file
def write_processed_file(processed_files):
    with open(PROCESSED_FILE, 'w') as f:
        f.write('\n'.join(processed_files))

from googleapiclient.http import MediaIoBaseDownload

# Define a function to check for new files in the specified Google Drive folder
def check_for_new_files():
    drive_service = build('drive', 'v3', credentials=credentials)
    query = f"'{SOURCE_FOLDER_ID}' in parents"
    results = drive_service.files().list(q=query, fields='nextPageToken, files(id, name)').execute()
    items = results.get('files', [])
    print(results)
    if not items:
        print('No new files found in the source folder.')
    else:
        processed_files = read_processed_file()
        new_items = [item for item in items if item['id'] not in processed_files]
        if not new_items:
            print('No new files found since the last run.')
        else:
            print(f'{len(new_items)} new files found since the last run.')
            gcs_uri = None  # Add this line to initialize the gcs_uri variable
            for item in new_items:
                file_id = item['id']
                file_name = item['name']
                print(f'Processing file {file_name} (ID: {file_id})')

            # Download the file to the input directory
            request = drive_service.files().get_media(fileId=file_id)
            with open(os.path.join(input_dir, file_name), 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    print(f"Download {int(status.progress() * 100)}.")

            # Convert the file to WAV format
            input_path = os.path.join(input_dir, file_name)
            output_filename = f"{os.path.splitext(file_name)[0]}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.wav"
            output_path = os.path.join(output_dir, output_filename)

            # Use FFmpeg to convert file to WAV format
            subprocess.call(["ffmpeg", "-i", input_path, "-acodec", "pcm_s16le", "-ar", "44100", "-f", "wav", output_path])

            # Upload the converted WAV file to Google Cloud Storage
            try:
                bucket_name = "speechtotext011"  # Replace with your Google Cloud Storage bucket name
                gcs_uri = upload_to_gcs(output_path, bucket_name)
                print(f"File uploaded to Google Cloud Storage: {gcs_uri}")
            except Exception as e:
                print(f"Error uploading file to Google Cloud Storage: {e}")

            # Transcribe the file using Google Speech-to-Text
            speech_client = speech.SpeechClient()

            audio = speech.RecognitionAudio(uri=gcs_uri)

            diarization_config = speech.SpeakerDiarizationConfig(
                enable_speaker_diarization=True,
                min_speaker_count=1,
                max_speaker_count=3,
            )

            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=44100,
                enable_speaker_diarization=True,
                diarization_speaker_count=2,
                model='phone_call',
                audio_channel_count=1,
                enable_separate_recognition_per_channel=True,
                diarization_config=diarization_config,
                language_code='en-US')

            transcription_successful = False
            try:
                operation = speech_client.long_running_recognize(config=config, audio=audio)

                response = operation.result(timeout=3000)
                result = response.results[-1]
                transcription_successful = True
            except Exception as e:
                if "Must use single channel (mono) audio" in str(e):
                    print(f"Error transcribing file {file_name} (ID: {file_id}): {e}")
                    print("Retrying with 2 audio channels.")
                    
                    # Update the audio_channel_count to 2
                    config.audio_channel_count = 2

                    try:
                        operation = speech_client.long_running_recognize(config=config, audio=audio)

                        response = operation.result(timeout=3000)
                        result = response.results[-1]
                        transcription_successful = True
                    except Exception as e:
                        print(f"Error transcribing file {file_name} (ID: {file_id}): {e}")
                else:
                    print(f"Error transcribing file {file_name} (ID: {file_id}): {e}")

            if transcription_successful:
                # Process the transcription result, save the output file, and upload it to Google Drive.

            # If you experience troubles with transcription consistency or quality you can print the full response for debugging purposes. Uncomment the below
            # print("Full response:")
            # print(response)

                words_info = result.alternatives[0].words

                tag = 1
                speaker = ""

                if words_info:
                    output_filename = f"{file_name}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_transcription.txt"
                    output_file = os.path.join(output_dir, output_filename)
                    with open(output_file, 'w') as f:
                        for word_info in words_info:
                            start_time = word_info.start_time
                            end_time = word_info.end_time

                            if word_info.speaker_tag == tag:
                                speaker = speaker + " " + word_info.word

                            else:
                                f.write("speaker {}: {} - {}:\n {}\n\n".format(tag, start_time.total_seconds() * 1.0, end_time.total_seconds() * 1.0, speaker))
                                tag = word_info.speaker_tag
                                speaker = "" + word_info.word

                        f.write("speaker {}: {} - {}:\n {}\n\n".format(tag, start_time.total_seconds() * 1.0, end_time.total_seconds() * 1.0, speaker))

                    print("Output saved to file: {}".format(output_file))
                else:
                    print("No transcription available.")

                # Upload the transcription file to the destination folder on Google Drive
                media = MediaFileUpload(output_file, mimetype='text/plain')
                file_metadata = {
                    'name': output_filename,
                    'parents': [DESTINATION_FOLDER_ID],
                }
                uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                print(f"Transcription file uploaded to Google Drive with ID: {uploaded_file.get('id')}")

                # Update the list of processed files
                processed_files.append(file_id)

            # Save the updated list of processed files
            write_processed_file(processed_files)

check_for_new_files()


                    
