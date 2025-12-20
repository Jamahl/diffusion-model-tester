# Development Tasks: SinkIn Image Experimentation Web App

This document outlines the step-by-step implementation plan for the local-first SinkIn Image Experimentation Web App. Each task should be completed, tested, and committed before moving to the next.

## Phase 1: Environment & Project Setup (Backend + Frontend)

### Task 1: Initialize Backend (FastAPI)
- Create `backend/` directory.
- Initialize Python virtual environment: `python -m venv venv`.
- Install dependencies: `fastapi`, `uvicorn`, `requests`, `python-multipart`, `pydantic`.
- Create `main.py` with a simple "Hello World" root endpoint.
- **Test**: `uvicorn main:app --reload` loads http://localhost:8000.
- **End State**: Basic FastAPI server running.

### Task 2: Initialize Frontend (SvelteKit)
- Run `npm create svelte@latest frontend` (Skeleton, TypeScript, ESLint, Prettier).
- `cd frontend`, `npm install`.
- Install DaisyUI and TailwindCSS: `npm i -D tailwindcss postcss autoprefixer daisyui`.
- Configure `tailwind.config.js` and `app.css`.
- **Test**: `npm run dev` loads http://localhost:5173 with Tailwind styles.
- **End State**: SvelteKit + Tailwind/DaisyUI setup.

### Task 3: Database & Multi-select Setup (SQLite)
- Create `backend/db/` directory and `database.py` for SQLite connection using SQLAlchemy or raw `sqlite3`.
- Define tables in `models.py`: `runs`, `images`, `configs`, `assets`, `jobs`.
- Implement `init_db` to create tables on startup.
- **Test**: Run script, `experiments.db` is created with correct tables.
- **End State**: SQLite database initialized.

---

## Phase 2: Core API Implementation (FastAPI)

### Task 4: SinkIn AI /inference Wrapper
- Implement `POST /api/jobs/run` that calls SinkIn AI `/inference`.
- Handle multi-part upload for `init_image` if present.
- Store `inf_id`, `raw_payload`, and `raw_response`.
- **Test**: Mock SinkIn API call and verify data in `images` and `configs` tables.
- **End State**: Backend can trigger inference and store results.

### Task 5: SinkIn AI /upscale Wrapper
- Implement `POST /api/images/{id}/upscale`.
- Support `esrgan` and `hires_fix` parameters.
- Update `images` table with `upscale_url`.
- **Test**: Trigger upscale for a mock image ID.
- **End State**: Backend can trigger upscaling.

### Task 6: Runs & Images Endpoints
- Implement `GET /api/runs`: Returns list with `total/unrated/upscaled` counts.
- Implement `GET /api/images`: Paginated, filters by `run_id`, `unrated_only`.
- Implement `POST /api/images/{id}/score`: Save 1-10 scores.
- **Test**: Verify CRUD operations via Swagger (http://localhost:8000/docs).
- **End State**: Basic data API functional.

---

## Phase 3: Frontend - Dashboard & Run Form

### Task 7: Layout & Navigation
- Create global layout with "Dashboard", "Run Form", "Review Panel".
- Implement state-based or URL-based navigation.
- **End State**: Navigation between main views works.

### Task 8: Run Form (Config UI)
- Build form with inputs: Prompt, Negative Prompt (multi-select default).
- Implement multi-select for Schedulers, Steps, Seed, and CFG. (review API docs to check what which configs we can put including seed and enter as an option for the other, all of the possible points to make it customisatable.
- Add Model selection (Fetch list from `GET /api/models` calling SinkIn `/models`).
- Add Init Image upload field.
- **Test**: Submit form and verify `POST /api/runs` creates a run and enqueues jobs.
- **End State**: Functional run configuration UI.

---

## Phase 4: Frontend - Review & Analysis

### Task 9: Image Review Panel (Gallery)
- Build paginated gallery of images for a specific Run.
- Implement "Unrated Only" toggle.
- **End State**: Gallery view with filters.

### Task 10: Single Image View & Keyboard Scoring
- Implement full-screen image view.
- Enable keyboard navigation (Arrows).
- Enable keyboard scoring (1-9 keys map to overall quality, 0 for 10).
- Post score to backend on keypress.
- **Test**: Cycle through images and score them using only keys.
- **End State**: High-speed scoring UI.

### Task 11: Upscale & Side-by-Side Review
- Add "Upscale" button to individual image view with options (ESRGAN/Hires Fix).
- Implement side-by-side view (Original vs Upscaled).
- **Test**: Click upscale, wait for completion, view comparison.
- **End State**: Integrated upscaling UI.


---

## Phase 5: Queue & Export

### Task 12: Queue Management
- Display "Upcoming Jobs" in Dashboard.
- Add "Run Next" button to process one job at a time.
- Show credit cost and progress status.
- **End State**: Controlled job execution.

### Task 13: CSV Export & Table View
- Create `GET /api/csv` endpoint joining `runs`, `images`, and `configs`.
- Add "Export to CSV" button in UI.
- Build a Table view for cross-run analysis. where you can see and rank all the scores like a spreadsheet. 
- **End State**: Data export functional.

---

## Phase 6: Polishing & Final Testing

### Task 14: Final Integration & Error Handling
- Ensure fallback to text2img works on img2img failure.
- Add Loading states and Toast notifications (e.g., "Image Upscaled", "Run Started").
- Final UX pass: Smooth transitions, dark mode support.
- **End State**: Fully functional, polished MVP.