import os
import random
from flask import Flask, request, jsonify, send_from_directory
from moviepy.editor import VideoFileClip, CompositeVideoClip, AudioFileClip, ImageClip, vfx
from gtts import gTTS
from flask_cors import CORS
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


# Monkey patch for the deprecated ANTIALIAS in PIL (Pillow)
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Define folders
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PROCESSED_FOLDER = os.path.join(BASE_DIR, 'processed')

# Define font path (update this to a valid font path on your system)
# For Windows users, it might be something like "C:/Windows/Fonts/arial.ttf"
FONT_PATH = "C:/Windows/Fonts/arial.ttf"  # Update this path as needed

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def save_video_file(video_file):
    try:
        filename = f"uploaded_video_{random.randint(1000, 9999)}.mp4"
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        video_file.save(video_path)
        logging.info(f"Video file saved at: {video_path}")
        return video_path
    except Exception as e:
        logging.error(f"Error saving video file: {e}")
        return None

def generate_ai_voice(text, gender):
    try:
        tld = 'com.au' if gender == 'female' else 'com'
        tts = gTTS(text=text, lang='en', slow=False, tld=tld)
        filename = f"voice_{random.randint(1000, 9999)}.mp3"
        voice_path = os.path.join(PROCESSED_FOLDER, filename)
        tts.save(voice_path)
        logging.info(f"AI voice file saved at: {voice_path}")
        return voice_path
    except Exception as e:
        logging.error(f"Error generating AI voice: {e}")
        return None

def generate_subtitle_image(text, video_size, font_path=FONT_PATH, fontsize=40, color="white"):
    """Generates an image of the subtitle text using Pillow."""
    img = Image.new("RGBA", video_size, (255, 255, 255, 0))
    try:
        font = ImageFont.truetype(font_path, fontsize)
    except Exception as e:
        logging.error(f"Error loading font {font_path}: {e}. Falling back to default font.")
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    # Use textbbox to get the bounding box of the text
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    position = ((video_size[0] - text_width) // 2, video_size[1] - text_height - 50)  # Centered at bottom
    draw.text(position, text, font=font, fill=color)
    logging.info(f"Subtitle image generated with text: '{text}' at position: {position}")
    return np.array(img)

def add_subtitles_frame_by_frame(video, subtitle_text):
    """Add subtitles to the video using an image overlay."""
    subtitle_image = generate_subtitle_image(subtitle_text, video.size)
    subtitle_clip = ImageClip(subtitle_image, duration=video.duration).set_position("bottom").set_opacity(0.8)
    video_with_subtitles = CompositeVideoClip([video, subtitle_clip])
    logging.info("Subtitles added to video.")
    return video_with_subtitles

def convert_to_portrait(video):
    """Convert the video to portrait mode (9:16) suitable for YouTube Shorts."""
    portrait_video = video.fx(vfx.resize, height=1920).fx(vfx.crop, width=1080, height=1920, x_center=video.w / 2, y_center=video.h / 2)
    logging.info("Converted video to portrait mode.")
    return portrait_video

import time  # Import for adding a delay after writing the file

def add_subtitles_to_video(video_path, subtitle_text, voice_path):
    try:
        logging.info(f"Loading video: {video_path}")
        video = VideoFileClip(video_path)
        logging.info(f"Video loaded. Duration: {video.duration}s, Size: {video.size}")

        audio_clip = AudioFileClip(voice_path)
        logging.info(f"Audio loaded: {voice_path}")

        portrait_video = convert_to_portrait(video)
        logging.info("Converted video to portrait mode.")

        video_with_subtitles = add_subtitles_frame_by_frame(portrait_video, subtitle_text)
        video_with_subtitles = video_with_subtitles.set_audio(audio_clip)
        logging.info("Added subtitles and audio.")

        output_filename = f"output_video_{random.randint(1000, 9999)}.mp4"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)

        # Check if output directory is accessible and writable
        if not os.path.exists(PROCESSED_FOLDER):
            logging.error(f"Processed folder does not exist: {PROCESSED_FOLDER}")
            return None
        if not os.access(PROCESSED_FOLDER, os.W_OK):
            logging.error(f"Write permission denied for processed folder: {PROCESSED_FOLDER}")
            return None

        logging.info(f"Saving video to: {output_path}")

        # Write the video file with exception handling
        try:
            video_with_subtitles.write_videofile(output_path, codec="libx264", audio_codec="aac", threads=4, preset="fast")
            logging.info(f"Video successfully saved at: {output_path}")
        except Exception as e:
            logging.error(f"Error during video file writing: {e}")
            return None

        # Adding a small delay to ensure file write completion
        time.sleep(2)

        # Ensure the video file was actually saved
        if not os.path.exists(output_path):
            logging.error(f"Output video path does not exist after saving: {output_path}")
            return None

        return output_path
    except Exception as e:
        logging.error(f"Error adding subtitles to video: {e}")
        return None


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'video' not in request.files:
            logging.error("No video file provided in the request.")
            return jsonify({'error': 'No video file provided'}), 400

        video_file = request.files['video']
        subtitle_text = request.form.get('text')
        gender = request.form.get('gender')

        if not subtitle_text:
            logging.error("Subtitle text is missing in the request.")
            return jsonify({'error': 'Subtitle text is required'}), 400

        if not gender:
            logging.error("Gender is missing in the request.")
            return jsonify({'error': 'Gender is required'}), 400

        logging.info("Saving uploaded video file.")
        video_path = save_video_file(video_file)
        if not video_path:
            logging.error("Failed to save uploaded video file.")
            return jsonify({'error': 'Failed to save video file'}), 500

        logging.info("Generating AI voice for subtitles.")
        voice_path = generate_ai_voice(subtitle_text, gender=gender)
        if not voice_path:
            logging.error("Failed to generate AI voice.")
            return jsonify({'error': 'Failed to generate AI voice'}), 500

        logging.info("Adding subtitles to the video.")
        output_video = add_subtitles_to_video(video_path, subtitle_text, voice_path)
        if not output_video or not os.path.exists(output_video):
            logging.error(f"Failed to create video: Output video path does not exist: {output_video}")
            return jsonify({'error': 'Failed to create video'}), 500

        # Optionally, you can serve the video via a Flask route
        video_filename = os.path.basename(output_video)
        video_url = f"/processed/{video_filename}"

        logging.info(f"Upload successful. Video available at: {video_url}")
        return jsonify({'video_url': video_url}), 200

    except Exception as e:
        logging.error(f"Error in processing request: {e}")
        return jsonify({'error': 'An internal error occurred. Please try again.'}), 500

@app.route('/processed/<filename>', methods=['GET'])
def serve_processed_video(filename):
    return send_from_directory(PROCESSED_FOLDER, filename)

@app.route('/delete', methods=['POST'])
def delete_files():
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        processed_path = data.get('processed_path')

        if video_path:
            abs_video_path = os.path.abspath(video_path)
            if os.path.exists(abs_video_path):
                os.remove(abs_video_path)
                logging.info(f"Deleted uploaded video: {abs_video_path}")

        if processed_path:
            abs_processed_path = os.path.abspath(processed_path)
            if os.path.exists(abs_processed_path):
                os.remove(abs_processed_path)
                logging.info(f"Deleted processed video: {abs_processed_path}")

        return jsonify({'message': 'Files deleted successfully'}), 200

    except Exception as e:
        logging.error(f"Error deleting files: {e}")
        return jsonify({'error': 'Failed to delete files'}), 500

if __name__ == '__main__':
    app.run(debug=True)
