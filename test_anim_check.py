import os
import subprocess
from pathlib import Path
import config
import video_editor

print("Testing enhanced animation pipeline...")
img_test = "temp/run_1791366319/scene_1_image.jpg"
audio_test = "temp/run_1791366319/scene_1_voice.wav"
out_test = "temp/test_optimized_anim.mp4"

if not os.path.exists(img_test) or not os.path.exists(audio_test):
    print("Test assets missing, exiting.")
else:
    captions = ["KLONING SUARA AI", "PENIPUAN MENIRU SUARA KERABATMU"]
    try:
        video_editor.render_animated_scene(
            image_path=img_test,
            captions=captions,
            audio_path=audio_test,
            output_scene_path=out_test,
            motion_type=1
        )
        print("Success! Generated:", out_test, "Size:", os.path.getsize(out_test))
    except Exception as e:
        print("Error:", e)
