# Workout CSV CLI

[![CI](https://github.com/ebarber321/workout-python/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ebarber321/workout-python/actions/workflows/ci.yml)

Local CSV-based workout logger and movement catalog.

Features
- Movements catalog in `movements.csv` (id,name,category,default_unit,primary_muscle,secondary_muscles,notes)
- One-row-per-set workout archive in `workouts.csv` (workout_id,date,start_time,movement_id,movement_name,set_number,set_type,cluster_id,reps,load,unit,rest_seconds,rpe,tags,notes,created_at)
- CLI: init, list-movements, find-movement, add-movement, import-movements, add-set, start-session, export-summary

Quickstart

1. Create CSV templates:

   python Main.py init

2. List movements:

   python Main.py list-movements

3. Find a movement:

   python Main.py find-movement --name bench

4. Add a set (example):

   python Main.py add-set --movement_id barbell_bench_press --set_number 1 --reps 5 --load 100 --unit kg

5. Export a workout summary CSV:

   python Main.py export-summary --out workouts_summary.csv

Testing

- Tests use pytest and are in `tests/test_main.py`.

  pip install -r requirements.txt
  pytest -q

Notes

- Movement ids are slugified names and are used when adding sets.
- The interactive `start-session` helps log multiple sets quickly.

CI / GitHub

- A GitHub Actions workflow is included at `.github/workflows/ci.yml` to run tests (pytest) on push and pull requests.
- To connect this folder to a GitHub repository and enable CI (recommended):

  1. Initialize git (if not already):

     ```bash
     git init
     git add .
     git commit -m "Initial import: workout CLI, tests, CI"
     ```

  2. Create a GitHub repo and push (option A: using GitHub CLI `gh`):

     ```bash
     gh repo create <OWNER>/<REPO> --public --source=. --remote=origin --push
     ```

     (Option B: create the repo on github.com, then set the remote and push):

     ```bash
     git remote add origin git@github.com:<OWNER>/<REPO>.git
     git branch -M main
     git push -u origin main
     ```

  3. After the first push, the Actions tab on GitHub will show the CI runs. The `ci.yml` workflow runs pytest on matrix Python versions.

Notes:
- Ensure `requirements.txt` lists your test dependencies (`pytest`).
- You can add a badge to this README once your GitHub repo exists.
