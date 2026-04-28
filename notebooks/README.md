# Custom Wakeword Training Guide

Train your own wakeword model using openWakeWord and your personal voice recordings. This guide walks you through every cell in the Colab notebook, from generating test clips to deploying the final model in your project.

---

## What You'll Need

- A Google account (for Colab and Google Drive)
- Audio recordings of people saying your wakeword (50+ samples recommended, any common audio format works)
- The `hey-kluky` project cloned on your machine

---

## Step-by-Step Walkthrough

### Step 1 — Download the Notebook & Open It in Google Colab

Before anything else, you need to get the training notebook into your own Google Colab environment.

1. **Download the notebook file** — grab the `train_custom_wakeword.ipynb` file from the `hey-kluky` repository (it's in the `notebooks/` folder). You can either clone the repo and find it locally, or download just the `.ipynb` file directly from GitHub.

2. **Upload it to your Google Drive:**
   - Go to [drive.google.com](https://drive.google.com)
   - Drag and drop the `.ipynb` file anywhere into your Drive, or use the **New → File upload** button.

3. **Open it in Google Colab:**
   - Find the uploaded `.ipynb` file in your Drive.
   - Double-click it — it should open in Google Colab automatically.
   - If it doesn't, right-click the file → **Open with → Google Colaboratory**.
   - If you don't see Google Colaboratory as an option, click **Connect more apps**, search for "Colaboratory", and install it.

4. **Optional but recommended — switch to a GPU runtime** for faster training:
   - In Colab, go to **Runtime → Change runtime type**.
   - Set **Hardware accelerator** to **GPU** (T4 is fine).
   - Click **Save**.

You're now ready to start running the cells in order.

---

### Cell 1 — Set Your Wakeword & Test Pronunciation

This cell installs the Piper TTS engine and generates a synthetic sample of your wakeword so you can hear how it sounds before committing to a full training run.

**What to do:**

1. Type your wakeword into the `target_word` field (e.g. `hey_klooky`).
2. Run the cell. It will install dependencies on the first run (takes a couple of minutes).
3. Listen to the generated audio clip that plays automatically.

**If the pronunciation sounds wrong**, try spelling it out phonetically with underscores separating syllables. For example: `hey siri` → `hey_seer_e`. Spell out any numbers (`2` → `two`) and avoid punctuation other than `?` and `!`.

Keep adjusting and re-running until the synthetic clip sounds natural. This matters because the training process will generate thousands of similar synthetic examples as positive training data.

---

### Cell 2 — Download Training Data

Run this cell as-is. It downloads everything the model needs for training:

- The openWakeWord library and its embedding models
- Room Impulse Responses (for adding realistic echo/reverb to training samples)
- Background noise from AudioSet
- Music clips from the Free Music Archive
- Pre-computed openWakeWord features (~2,000 hours of speech for negative examples)
- A validation set for false-positive rate estimation

This step takes roughly **15–20 minutes**. No configuration needed — just run it and wait.

> **License note:** The downloaded data has mixed licenses. Models trained with this data should be considered for **non-commercial personal use only**.

---

### Cell 2.4 — Connect Google Drive & Locate Your Samples

This cell mounts your Google Drive so the notebook can access your personal wakeword recordings.

**What to do:**

1. Set the `folder_path` field to the path inside your Google Drive where your audio samples are stored. For example:
   - `wakeword_samples`
   - `projects/my_wakeword/recordings`
   - `audio/hey_jarvis`

   This path is relative to `My Drive`, so `wakeword_samples` means `My Drive/wakeword_samples`.

2. Run the cell. It will ask you to authorize Google Drive access — follow the prompts.

3. Check the output. It will list all detected audio files in your folder.

If the folder doesn't exist yet, the cell creates it for you. Upload your recordings there via the Google Drive web interface or mobile app, then re-run the cell to confirm they're detected.

**Recording tips:**

- Aim for **50+ samples** minimum — more is better.
- Use **different speakers** if possible (friends, family).
- Record in **varied environments** (quiet room, with background noise, different distances from the mic).
- Any common audio format works: m4a, mp3, ogg, flac, aac, wma, opus, webm, wav, and more.

---

### Cell 2.5 — Convert Samples to Training Format

This cell converts all your audio recordings to the format openWakeWord expects: **16 kHz, mono, 16-bit PCM WAV**.

**What to do:**

1. Make sure you ran Cell 2.4 first (this cell depends on the `SAMPLES_FOLDER` variable it sets).
2. Run the cell. It installs ffmpeg if needed and converts every supported audio file it finds.
3. Check the output summary — it reports how many files were converted, skipped (already converted), or failed.

If any files fail, check that they're valid audio files and not corrupted.

---

### Cell 3 — Train the Model

This is the main training cell. It generates synthetic positive examples, augments them, and trains the wakeword detection model.

**Parameters you can tweak:**

| Parameter | Default | What it does |
|---|---|---|
| `number_of_examples` | 500 | How many synthetic examples to generate. More = better but slower. For best results use 30,000–50,000. |
| `number_of_training_steps` | 10,000 | How long to train. More steps generally improves accuracy. |
| `false_activation_penalty` | 1,500 | How aggressively false activations are penalized. Higher = fewer false triggers but the model may also miss some real activations. |

**What to do:**

1. Adjust the sliders if you want (defaults are fine for a first attempt).
2. Run the cell. With default values on a CPU runtime, training takes **30–60 minutes**. Switch to a GPU runtime for significantly faster training.
3. When training completes, the `.onnx` and `.tflite` model files are automatically downloaded to your computer.

If the automatic download doesn't trigger, navigate to the `my_custom_model` folder in the Colab file browser (folder icon on the left sidebar) and download the files manually.

---

## After Training — Deploy to hey-kluky

Once you have your `.onnx` model file, follow these steps to integrate it:

1. **Copy the model file** into the `hey-kluky/wakeword_model/` directory in your project.

2. **Update your `.env` file** — set the `WAKEWORD_MODEL_NAME` variable to the name of your model file **without** the `.onnx` extension:

   ```
   WAKEWORD_MODEL_NAME=hey_klooky
   ```

   So if your file is called `hey_klooky.onnx`, the value is just `hey_klooky`.

3. Start the application. It will load your custom wakeword model on startup.

---

## Troubleshooting

**The synthetic pronunciation sounds wrong in Cell 1**
Experiment with phonetic spelling. Underscores act as syllable separators. Try exaggerating vowels or consonants until it sounds right.

**Cell 2.5 says "0 audio files detected"**
Make sure you uploaded files to the correct Google Drive folder and that the `folder_path` in Cell 2.4 matches. Re-run Cell 2.4 to verify.

**Training produces a model that triggers too often (false positives)**
Increase `false_activation_penalty` (try 2,000–3,000) and re-train. Adding more real voice samples also helps.

**Training produces a model that misses the wakeword (false negatives)**
Lower `false_activation_penalty`, increase `number_of_examples` to 5,000+, and make sure your recordings are clear.

**Tensor size mismatch errors during training**
This usually means you don't have enough samples. Try to get at least 50 real recordings and set `number_of_examples` to at least 1,000 for synthetic generation.

**Cell execution order matters**
The cells must be run in order: 1 → 2 → 2.4 → 2.5 → 3. Cell 2.5 depends on variables set in Cell 2.4, and Cell 3 depends on variables from both Cell 1 (`target_word`) and Cell 2.5 (`OUTPUT_DIR`).
