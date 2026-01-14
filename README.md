# SinkIn Image Experimentation Web App

A local-first web application for text-to-image and img2img experiments using SinkIn AI's Stable Diffusion models. Build for rapid experimentation, scoring, and analysis of AI-generated images.

## Project Overview

This application allows you to:
- Run controlled text-to-image experiments via SinkIn AI's `/inference` API
- Upscale generated images using ESRGAN or Hires Fix via SinkIn AI's `/upscale` API
- Store every input, setting, and response in a local SQLite database
- Rapidly review and score generated images with keyboard-driven navigation
- Support batch runs, queueing, and CSV analysis
- Compare results across different models, schedulers, and parameters

## Tech Stack

- **Frontend**: SvelteKit with TypeScript, TailwindCSS, and DaisyUI
- **Backend**: Python FastAPI with SQLite database
- **API Integration**: SinkIn AI API for image generation and upscaling
- **Storage**: Local filesystem for images and assets

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- SinkIn AI API key

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your SinkIn AI API key as an environment variable:
```bash
export SINKIN_API_KEY="your_api_key_here"  # On Windows: set SINKIN_API_KEY="your_api_key_here"
```

5. Start the backend server:
```bash
uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Usage

1. **Create Experiments**: Use the Run Form to configure prompts, models, and parameters
2. **Generate Images**: Queue and run experiments using SinkIn AI's models
3. **Review & Score**: Navigate through generated images using keyboard shortcuts (1-9 for scoring, arrow keys for navigation)
4. **Upscale Images**: Enhance selected images with ESRGAN or Hires Fix
5. **Analyze Results**: Export data to CSV and compare results across runs

## Key Features

- **Keyboard-Driven Scoring**: Fast image evaluation with number keys (1-9) and navigation (arrow keys)
- **Batch Experiments**: Test multiple prompts, models, and parameters simultaneously
- **Queue Management**: Control job execution and monitor progress
- **Side-by-Side Comparison**: Compare original and upscaled images
- **Data Export**: Export all experiment data to CSV for analysis
- **Local Storage**: All data stored locally in SQLite database

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

## Development

The project follows a task-based development approach. See `tasks.md` for detailed implementation steps and `architecture.md` for technical specifications.

## License

Private project - All rights reserved.
