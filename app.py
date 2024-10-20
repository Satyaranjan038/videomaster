import os
import random
from flask import Flask, request, jsonify, send_file
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from gtts import gTTS
from flask_cors import CORS
import logging

app = Flask(__name__)


CORS(app, resources={r"/*": {"origins": "*"}})
# Set up logging to track errors
logging.basicConfig(level=logging.INFO)

def save_video_file(video_file):
    try:
        video_path = f"uploaded_video_{random.randint(1000, 9999)}.mp4"
        video_file.save(video_path)
        logging.info(f"Video file saved at: {video_path}")
        return video_path
    except Exception as e:
        logging.error(f"Error saving video file: {e}")
        return None

def generate_ai_voice(text, gender):
    try:
        # Use Google Text-to-Speech (gTTS) to generate AI voice
        tts = gTTS(text=text, lang='en', slow=False, tld='com.au' if gender == 'female' else 'com')
        voice_path = f"voice_{random.randint(1000, 9999)}.mp3"
        tts.save(voice_path)
        logging.info(f"AI voice file saved at: {voice_path}")
        return voice_path
    except Exception as e:
        logging.error(f"Error generating AI voice: {e}")
        return None

def add_subtitles_to_video(video_path, subtitle_text, voice_path):
    try:
        # Load video and voice
        video = VideoFileClip(video_path)
        audio = voice_path if os.path.exists(voice_path) else None

        if not audio:
            logging.error("AI voice file not found.")
            return None

        # Add subtitles
        subtitle_clip = TextClip(subtitle_text, fontsize=24, color='white', size=video.size)
        subtitle_clip = subtitle_clip.set_duration(video.duration).set_position(('center', 'bottom'))

        # Create composite video with audio and subtitles
        video_with_subtitles = CompositeVideoClip([video, subtitle_clip])
        video_with_subtitles = video_with_subtitles.set_audio(audio)

        # Save the final video
        output_path = f"output_video_{random.randint(1000, 9999)}.mp4"
        video_with_subtitles.write_videofile(output_path, codec="libx264", audio_codec="aac")

        logging.info(f"Video with subtitles saved at: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error adding subtitles to video: {e}")
        return None

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if video file is provided
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        video_file = request.files['video']
        subtitle_text = request.form.get('text')
        gender = request.form.get('gender')

        if not subtitle_text:
            return jsonify({'error': 'Subtitle text is required'}), 400

        if not gender:
            return jsonify({'error': 'Gender is required'}), 400

        # Save uploaded video
        video_path = save_video_file(video_file)
        if not video_path:
            return jsonify({'error': 'Failed to save video file'}), 500

        # Generate AI voice
        voice_path = generate_ai_voice(subtitle_text, gender=gender)
        if not voice_path:
            return jsonify({'error': 'Failed to generate AI voice'}), 500

        # Add subtitles and AI voice to video
        output_video = add_subtitles_to_video(video_path, subtitle_text, voice_path)
        if not output_video or not os.path.exists(output_video):
            return jsonify({'error': 'Failed to create video'}), 500

        # Return the final video file as download
        return send_file(output_video, as_attachment=True)

    except Exception as e:
        logging.error(f"Error in processing request: {e}")
        return jsonify({'error': 'An internal error occurred. Please try again.'}), 500

if __name__ == '__main__':
    app.run(debug=True)
