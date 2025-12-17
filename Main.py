"""Workout CSV utilities and richer CLI

Features:
- Movement catalog: load, search, import, add
- Workout archive: append sets (one-row-per-set), export summary
- Interactive session flow to add multiple sets
"""

from __future__ import annotations

import argparse
import csv
import datetime
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).parent
MOVEMENTS_CSV = BASE_DIR / "movements.csv"
WORKOUTS_CSV = BASE_DIR / "workouts.csv"

SET_TYPE_CHOICES = {
	"warmup",
	"ramp",
	"work",
	"heavy",
	"drop",
	"backoff",
	"amrap",
	"superset",
	"rest-pause",
	"failure",
	"accessory",
	"bilbo",
}


@dataclass
class Movement:
	id: str
	name: str
	category: str = ""
	default_unit: str = ""
	primary_muscle: str = ""
	secondary_muscles: str = ""
	notes: str = ""


@dataclass
class SetRecord:
	workout_id: str
	date: str
	start_time: str
	movement_id: str
	movement_name: str
	set_number: int
	set_type: str = "work"
	cluster_id: str = ""
	reps: Optional[str] = ""
	load: Optional[float] = None
	unit: str = ""
	rest_seconds: Optional[int] = None
	rpe: Optional[float] = None
	tags: str = ""
	notes: str = ""
	created_at: str = ""


def ensure_files_exist() -> None:
	"""Create CSV files with headers if they do not exist."""
	if not MOVEMENTS_CSV.exists():
		MOVEMENTS_CSV.write_text(
			"id,name,category,default_unit,primary_muscle,secondary_muscles,notes\n"
		)
		print(f"Created {MOVEMENTS_CSV}")

	if not WORKOUTS_CSV.exists():
		WORKOUTS_CSV.write_text(
			(
				"workout_id,date,start_time,movement_id,movement_name,set_number,set_type,cluster_id,"
				"reps,load,unit,rest_seconds,rpe,tags,notes,created_at\n"
			)
		)
		print(f"Created {WORKOUTS_CSV}")


def slugify(name: str) -> str:
	s = name.strip().lower().replace(" ", "_")
	s = "".join(ch for ch in s if ch.isalnum() or ch == "_")
	return s[:40]


def load_movements() -> Dict[str, Movement]:
	movements: Dict[str, Movement] = {}
	if not MOVEMENTS_CSV.exists():
		return movements
	with MOVEMENTS_CSV.open("r", encoding="utf-8", newline="") as fh:
		reader = csv.DictReader(fh)
		for row in reader:
			mid = row.get("id") or slugify(row.get("name", ""))
			movements[mid] = Movement(
				id=mid,
				name=row.get("name", ""),
				category=row.get("category", ""),
				default_unit=row.get("default_unit", ""),
				primary_muscle=row.get("primary_muscle", ""),
				secondary_muscles=row.get("secondary_muscles", ""),
				notes=row.get("notes", ""),
			)
	return movements


def save_movements(movs: List[Movement]) -> None:
	with MOVEMENTS_CSV.open("w", encoding="utf-8", newline="") as fh:
		writer = csv.writer(fh)
		writer.writerow(["id", "name", "category", "default_unit", "primary_muscle", "secondary_muscles", "notes"])
		for m in movs:
			writer.writerow([m.id, m.name, m.category, m.default_unit, m.primary_muscle, m.secondary_muscles, m.notes])


def append_movement(m: Movement) -> None:
	ensure_files_exist()
	movements = load_movements()
	if m.id in movements:
		raise ValueError(f"movement id already exists: {m.id}")
	with MOVEMENTS_CSV.open("a", encoding="utf-8", newline="") as fh:
		writer = csv.writer(fh)
		writer.writerow([m.id, m.name, m.category, m.default_unit, m.primary_muscle, m.secondary_muscles, m.notes])
	print(f"Added movement {m.id} - {m.name}")


def find_movements(query: str) -> List[Movement]:
	q = query.lower()
	movements = load_movements()
	return [m for m in movements.values() if q in m.name.lower() or q in m.id.lower()]


def append_set_record(record: SetRecord) -> None:
	ensure_files_exist()
	if not record.created_at:
		record.created_at = datetime.datetime.now().isoformat()
	with WORKOUTS_CSV.open("a", encoding="utf-8", newline="") as fh:
		writer = csv.writer(fh)
		writer.writerow([
			record.workout_id,
			record.date,
			record.start_time,
			record.movement_id,
			record.movement_name,
			record.set_number,
			record.set_type,
			record.cluster_id,
			record.reps,
			record.load if record.load is not None else "",
			record.unit,
			record.rest_seconds if record.rest_seconds is not None else "",
			record.rpe if record.rpe is not None else "",
			record.tags,
			record.notes,
			record.created_at,
		])
	print(f"Appended set: {record.workout_id} {record.movement_name} set {record.set_number}")


def export_summary(out: Path) -> int:
	"""Export one-row-per-workout summary CSV into `out` path."""
	if not WORKOUTS_CSV.exists():
		return 0
	rows = []
	with WORKOUTS_CSV.open("r", encoding="utf-8", newline="") as fh:
		reader = csv.DictReader(fh)
		tmp = {}
		for r in reader:
			wid = r["workout_id"]
			tmp.setdefault(wid, {"workout_id": wid, "date": r.get("date", ""), "movements": []})
			tmp[wid]["movements"].append(f"{r.get('movement_name')}:{r.get('set_number')}x{r.get('reps')}@{r.get('load')}")
		rows = list(tmp.values())
	with out.open("w", encoding="utf-8", newline="") as fh:
		writer = csv.writer(fh)
		writer.writerow(["workout_id", "date", "movements_summary"])
		for r in rows:
			writer.writerow([r["workout_id"], r["date"], ";".join(r["movements"])])
	return len(rows)


def import_movements_file(path: Path) -> int:
	"""Import movements from a TSV/CSV that has at least Exercise_Name and Movement_Group or Body_Region."""
	if not path.exists():
		raise FileNotFoundError(path)
	text = path.read_text(encoding="utf-8")
	first_line = text.splitlines()[0]
	delimiter = "\t" if "\t" in first_line else ","
	reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
	count = 0
	existing = load_movements()
	for row in reader:
		name = (row.get("Exercise_Name") or row.get("Exercise Name") or row.get("Exercise") or "").strip()
		if not name:
			continue
		# deduplicate by name
		if any(m.name.lower() == name.lower() for m in existing.values()):
			continue
		mid = slugify(name)
		i = 1
		while mid in existing:
			i += 1
			mid = f"{slugify(name)}_{i}"
		m = Movement(id=mid, name=name, category=(row.get("Movement_Group") or "").strip())
		append_movement(m)
		existing[mid] = m
		count += 1
	return count


def cmd_init(args: argparse.Namespace) -> None:
	ensure_files_exist()
	print("Initialization complete.")


def cmd_list_movements(args: argparse.Namespace) -> None:
	movements = load_movements()
	if not movements:
		print("No movements found. Run 'init' or add movements.")
		return
	for m in movements.values():
		print(f"{m.id}\t{m.name}\t{m.category}\t{m.default_unit}")


def cmd_find_movement(args: argparse.Namespace) -> None:
	results = find_movements(args.name)
	if not results:
		print("No matches")
		return
	for m in results:
		print(f"{m.id}\t{m.name}\t{m.category}")


def cmd_add_movement(args: argparse.Namespace) -> None:
	mid = args.id or slugify(args.name)
	m = Movement(id=mid, name=args.name, category=args.category or "", default_unit=args.default_unit or "", primary_muscle=args.primary_muscle or "", secondary_muscles=args.secondary_muscles or "", notes=args.notes or "")
	append_movement(m)


def cmd_add_set(args: argparse.Namespace) -> None:
	movements = load_movements()
	movement = None
	if args.movement_id:
		movement = movements.get(args.movement_id)
	if not movement and args.movement_name:
		movement = next((m for m in movements.values() if m.name.lower() == args.movement_name.lower()), None)
	if not movement and args.movement_name:
		# auto-create
		movement = Movement(id=slugify(args.movement_name), name=args.movement_name)
		append_movement(movement)

	if not movement:
		print("Movement not found. Provide --movement-id or --movement-name to auto-create.")
		sys.exit(1)

	if args.set_type and args.set_type not in SET_TYPE_CHOICES:
		print(f"Warning: set_type '{args.set_type}' not in known choices")

	wid = args.workout_id or str(uuid.uuid4())[:8]
	now = datetime.datetime.now()
	rec = SetRecord(
		workout_id=wid,
		date=args.date or now.date().isoformat(),
		start_time=args.start_time or now.time().strftime("%H:%M:%S"),
		movement_id=movement.id,
		movement_name=movement.name,
		set_number=int(args.set_number),
		set_type=args.set_type or "work",
		cluster_id=args.cluster_id or "",
		reps=str(args.reps) if args.reps is not None else "",
		load=float(args.load) if args.load is not None else None,
		unit=args.unit or movement.default_unit or "",
		rest_seconds=int(args.rest_seconds) if args.rest_seconds is not None else None,
		rpe=float(args.rpe) if args.rpe is not None else None,
		tags=args.tags or "",
		notes=args.notes or "",
		created_at=now.isoformat(),
	)
	append_set_record(rec)


def cmd_import_movements(args: argparse.Namespace) -> None:
	n = import_movements_file(Path(args.file))
	print(f"Imported {n} movements")


def cmd_export_summary(args: argparse.Namespace) -> None:
	out = Path(args.out or "workouts_summary.csv")
	n = export_summary(out)
	print(f"Exported {n} workouts to {out}")


def cmd_start_session(args: argparse.Namespace) -> None:
	"""Interactive flow: ask for session metadata and repeatedly add sets."""
	ensure_files_exist()
	wid = args.workout_id or str(uuid.uuid4())[:8]
	date = args.date or datetime.date.today().isoformat()
	start_time = datetime.datetime.now().time().strftime("%H:%M:%S")
	print(f"Starting session {wid} on {date} (press enter without movement to finish)")
	set_num = 1
	while True:
		mv = input("Movement name (or blank to finish): ").strip()
		if not mv:
			break
		mlist = find_movements(mv)
		if mlist:
			chosen = mlist[0]
			print(f"Found: {chosen.id} - {chosen.name}")
		else:
			chosen = Movement(id=slugify(mv), name=mv)
			append_movement(chosen)
		reps = input("Reps (e.g., 5 or AMRAP): ").strip()
		load = input("Load (leave blank for bodyweight): ").strip()
		unit = input("Unit (kg/lb/bodyweight) [enter for default]: ").strip() or chosen.default_unit
		set_type = input("Set type (work/warmup/drop) [work]: ").strip() or "work"
		rec = SetRecord(
			workout_id=wid,
			date=date,
			start_time=start_time,
			movement_id=chosen.id,
			movement_name=chosen.name,
			set_number=set_num,
			set_type=set_type,
			reps=reps,
			load=float(load) if load else None,
			unit=unit or "",
			created_at=datetime.datetime.now().isoformat(),
		)
		append_set_record(rec)
		set_num += 1


def build_parser() -> argparse.ArgumentParser:
	p = argparse.ArgumentParser(description="Workout CSV helper CLI")
	sub = p.add_subparsers(dest="cmd")

	sub_init = sub.add_parser("init", help="Create CSV templates if missing")
	sub_init.set_defaults(func=cmd_init)

	sub_list = sub.add_parser("list-movements", help="List movements from catalog")
	sub_list.set_defaults(func=cmd_list_movements)

	fnd = sub.add_parser("find-movement", help="Find movement by name or id substring")
	fnd.add_argument("--name", required=True)
	fnd.set_defaults(func=cmd_find_movement)

	add_mov = sub.add_parser("add-movement", help="Add a movement to movements.csv")
	add_mov.add_argument("--id", help="movement id (short)")
	add_mov.add_argument("--name", required=True, help="movement name")
	add_mov.add_argument("--category", help="category")
	add_mov.add_argument("--default_unit", help="kg|lb|bodyweight")
	add_mov.add_argument("--primary_muscle", help="primary muscle")
	add_mov.add_argument("--secondary_muscles", help="secondary muscles (semicolon separated)")
	add_mov.add_argument("--notes", help="notes")
	add_mov.set_defaults(func=cmd_add_movement)

	add_set = sub.add_parser("add-set", help="Append a set to workouts.csv")
	add_set.add_argument("--workout_id", help="existing workout id (optional)")
	add_set.add_argument("--date", help="YYYY-MM-DD")
	add_set.add_argument("--start_time", help="HH:MM:SS")
	add_set.add_argument("--movement_id", help="movement id from catalog")
	add_set.add_argument("--movement_name", help="movement name (will auto-create if missing)")
	add_set.add_argument("--set_number", required=True, help="set number in sequence")
	add_set.add_argument("--set_type", help="warmup|work|drop|etc")
	add_set.add_argument("--cluster_id", help="group id for supersets/drop clusters")
	add_set.add_argument("--reps", help="reps (use 'AMRAP' or number)")
	add_set.add_argument("--load", help="load (numeric)")
	add_set.add_argument("--unit", help="kg|lb|bodyweight")
	add_set.add_argument("--rest_seconds", help="rest time in seconds")
	add_set.add_argument("--rpe", help="rpe")
	add_set.add_argument("--tags", help="semicolon separated tags")
	add_set.add_argument("--notes", help="notes")
	add_set.set_defaults(func=cmd_add_set)

	imp = sub.add_parser("import-movements", help="Import movements from TSV/CSV file")
	imp.add_argument("--file", required=True, help="path to TSV/CSV file to import")
	imp.set_defaults(func=cmd_import_movements)

	exp = sub.add_parser("export-summary", help="Export one-row-per-workout summary CSV")
	exp.add_argument("--out", help="output path (default: workouts_summary.csv)")
	exp.set_defaults(func=cmd_export_summary)

	start = sub.add_parser("start-session", help="Interactive session flow to log multiple sets")
	start.add_argument("--workout_id", help="optional workout id to use")
	start.add_argument("--date", help="YYYY-MM-DD")
	start.set_defaults(func=cmd_start_session)

	return p


def main(argv=None):
	parser = build_parser()
	args = parser.parse_args(argv)
	if not getattr(args, "cmd", None):
		parser.print_help()
		return
	args.func(args)


if __name__ == "__main__":
	main()
