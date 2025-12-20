# Final PRD: SinkIn Image Experimentation Web App

This document outlines the architecture and requirements for the **SinkIn Image Experimentation Web App**, a local-first platform for text-to-image and img2img experiments using SinkIn AI's Stable Diffusion models.

## Product Overview

### Goal
Build a local-first web application to:
- Run controlled text-to-image experiments via SinkIn AI's `/inference` API.
- Upscale generated images using ESRGAN or Hires Fix via SinkIn AI's `/upscale` API.
- Store every input, setting, full API payload, and response in a local SQLite database.
- Rapidly review and score generated images with a high-throughput keyboard-driven side-by-side UX.
- Support batch runs, queueing, and CSV analysis.

### Primary User
Single power user experimenting with Stable Diffusion models, schedulers, seeds, and upscaling parameters.

### Tech Stack
- **Frontend**: Svelte / SvelteKit (Fast image galleries, keyboard scoring)
- **Backend**: Python (FastAPI) (Better file handling, requests library for multipart uploads)
- **Database**: SQLite (Local storage for metadata, jobs, and configs)
- **API Integration**: SinkIn AI API (`/inference`, `/upscale`, `/models`)
- **Storage**: Local filesystem for images and assets

---

## Core Use Cases
1. **Start Batch Experiments**: Enter prompts, select models, resolutions, and settings to generate $N$ images.
2. **Review & Score**: Fast keyboard-driven scoring and navigation (1-10 keys), featuring side-by-side comparison for upscales.
3. **Upscale**: Enhance images in the viewer panel with ESRGAN or Hires Fix.
4. **Manage Queue**: Enqueue multiple variations and execute them in sequence.
5. **Analyze Results**: Filter runs, browse images, and export joined data to CSV.

---

## Experiment Generation

### Run Configuration
- **Prompts**: `prompt`, `negative_prompt` (supports `use_default_neg: "true"`)
- **Model**: `model_id` (e.g., "yBG2r9O" for majicMIX realistic; fetched via `/models`)
- **Dimensions**: `width`, `height` (128-896, increments of 8; default 512x768)
- **Run Sizing**: 
    - `total_images` (Default: 100)
    - `variations_count`: Number of queued copies to add to upcoming jobs.
- **Advanced Parameters**:
    - **Schedulers**: Multi-select (DPMSolverMultistep, K_EULER_ANCESTRAL, DDIM, etc.)
    - **Steps**: Multi-value numeric (1-50, default 30)
    - **Guidance Scale (CFG)**: Multi-value numeric (1-20, default 7.5)
    - **Seed Mode**: `random_per_image` (default), `fixed`, `seed_list`
    - **Num Images**: Number of images per API call (default 4)
    - **LoRA**: `lora` and `lora_scale` (optional)

### Img2Img / ControlNet
- **Init Image**: Optional `init_image_file` upload.
- **Strength**: `image_strength` (0-1, default 0.75).
- **ControlNet**: Support for `canny`, `depth`, `openpose`.
- **Fallback**: Fallback to text2img if img2img errors.

### Upscale Feature
- Triggered from the image view panel.
- **Types**:
    - `esrgan`: Scale 2-4 (default 2).
    - `hires_fix`: Strength 0-1 (default 0.6).
- **Behavior**: POSTs to `/upscale` using stored `inf_id` or image URL. Saves `upscale_url` and logs credit cost.

---

## Data Model (SQLite)

**Database**: `experiments.db`

### `runs` table
- `id` (UUID PK)
- `batch_number` (Integer, Unique)
- `name`, `created_at`, `prompt`, `negative_prompt`, `model_id`, `version`

### `images` table
- `id` (UUID PK)
- `run_id` (FK)
- `file_path`, `upscale_url`, `inf_id`, `created_at`
- **Scoring**: `overall_quality`, `anatomy_score`, `use_again` (yes/no/test_more), `prompt_adherence`, `background_score`

### `configs` table
- `id` (PK), `image_id` (FK Unique)
- `steps`, `scale`, `width`, `height`, `seed`, `scheduler`, `image_strength`, `controlnet`
- `credit_cost`, `raw_payload_json`, `raw_response_json`

### `assets` table (Uploaded inputs)
- `id` (UUID PK), `original_filename`, `mime_type`, `file_path`

### `jobs` (Queue)
- `id` (PK), `status` (queued/running/completed/failed)
- `config_json`, `init_image_asset_id` (FK)

---

## Backend API (FastAPI)

- `POST /api/runs`: Create run, compute combinations, enqueue jobs, and start generation.
- `GET /api/runs`: List runs with summary counts (total/unrated/upscaled).
- `POST /api/jobs/run`: Process the queue via SinkIn `/inference`.
- `GET /api/images`: Paginated list with filters (`run_id`, `unrated_only`).
- `POST /api/images/{id}/upscale`: Trigger SinkIn `/upscale` and update DB.
- `POST /api/images/{id}/score`: Save scores to DB.
- `GET /api/csv`: Export joined experiment data.
- **Static Assets**: Serves `/images/{id}.png` and `/assets/{id}`.
- **Analysis Endpoints**:
    - `GET /api/analysis/csv`: Stream comprehensive CSV export.
    - `GET /api/analysis/table`: Retrieve flattened JSON for cross-run comparison.
- **Queue Management**:
    - `DELETE /api/jobs/{id}`: Cancel a specific job.
    - `POST /api/jobs/cancel-all`: Purge the entire queue.

---

## Svelte UI

### Dashboard
- **Runs Table**: Display batch number, name, prompt, credit costs, and rated/unrated counts.
- **Active Queue**: 
    - Real-time display of queued jobs with "Cancel" buttons for individual jobs.
    - "Run Next" button to trigger synchronous job execution.
    - "Cancel All" to purge the queue.
- **CSV Export**: Global button to download all experiment data.

### Run Form
- **Parameter Matrix**: Support for multi-select schedulers and multi-value numeric inputs (steps, scale).
- **Batch Setup**: Automatically computes total jobs based on parameter combinations.
- **Init Image**: File upload for img2img and ControlNet workflows.
- **Queue Preview**: Review batches before starting the full experiment.

### Image Viewer / Review Panel
- **High-Speed Scoring**:
    - `1-0` keys for 1-10 "Overall Quality" scoring with automatic navigation to the next image.
    - **Detailed Review**: Dedicated card for rating "Anatomy", "Prompt Adherence", "Background", and "Use Again" (Yes/No/Maybe).
- **Navigation**: Arrow keys for manual cycling; Tooltips for all parameters.
- **Upscale Comparison**: Side-by-side or overlay view of original vs upscaled result.

### Analysis Page
- **Comparison Table**: Spreadsheet-style view of all images across all runs.
- **Search & Sort**: Filter by prompt, model, or run name; sort by batch, model, or performance metrics.
- **Direct Drill-down**: Clickable thumbnails and "View" buttons to jump to the review detail.

### Notifications
- **Global Toasts**: Non-intrusive feedback for image uploads, job completions, and errors.