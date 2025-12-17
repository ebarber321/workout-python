import csv
import io
import os
from pathlib import Path
import pytest

import Main as M


def test_ensure_files_exist_creates_files(tmp_path, monkeypatch):
    mfile = tmp_path / "movements.csv"
    wfile = tmp_path / "workouts.csv"
    monkeypatch.setattr(M, "MOVEMENTS_CSV", mfile)
    monkeypatch.setattr(M, "WORKOUTS_CSV", wfile)

    assert not mfile.exists()
    assert not wfile.exists()
    M.ensure_files_exist()
    assert mfile.exists()
    assert wfile.exists()
    # check headers
    with mfile.open("r", encoding="utf-8") as fh:
        first = fh.readline().strip()
    assert first.startswith("id,name")


def test_append_and_load_movement(tmp_path, monkeypatch):
    mfile = tmp_path / "movements.csv"
    monkeypatch.setattr(M, "MOVEMENTS_CSV", mfile)

    mov = M.Movement(id="foo", name="Foo Lift", category="Test")
    M.append_movement(mov)
    loaded = M.load_movements()
    assert "foo" in loaded
    assert loaded["foo"].name == "Foo Lift"


def test_append_set_and_export_summary(tmp_path, monkeypatch):
    mfile = tmp_path / "movements.csv"
    wfile = tmp_path / "workouts.csv"
    out = tmp_path / "out.csv"
    monkeypatch.setattr(M, "MOVEMENTS_CSV", mfile)
    monkeypatch.setattr(M, "WORKOUTS_CSV", wfile)

    # add a movement
    mv = M.Movement(id="bar", name="Barbell Press")
    M.append_movement(mv)

    rec = M.SetRecord(
        workout_id="w1",
        date="2025-01-01",
        start_time="12:00:00",
        movement_id=mv.id,
        movement_name=mv.name,
        set_number=1,
        reps="5",
        load=100.0,
        unit="kg",
        created_at="2025-01-01T12:00:00",
    )
    M.append_set_record(rec)

    n = M.export_summary(out)
    assert n == 1
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "workout_id" in text
    assert "w1" in text


def test_import_movements_file(tmp_path, monkeypatch):
    mfile = tmp_path / "movements.csv"
    monkeypatch.setattr(M, "MOVEMENTS_CSV", mfile)

    tsv = tmp_path / "import.tsv"
    tsv.write_text("Exercise_Name\tMovement_Group\nSnatch\tFull Body\nClean\tFull Body\n", encoding="utf-8")
    n = M.import_movements_file(tsv)
    assert n == 2
    loaded = M.load_movements()
    assert any("snatch" in k for k in loaded)


def test_find_movement(tmp_path, monkeypatch):
    mfile = tmp_path / "movements.csv"
    monkeypatch.setattr(M, "MOVEMENTS_CSV", mfile)

    M.append_movement(M.Movement(id="a1", name="Alpha"))
    M.append_movement(M.Movement(id="b2", name="Beta"))

    res = M.find_movements("alp")
    assert len(res) == 1
    assert res[0].id == "a1"


def test_cli_init_and_list(tmp_path, monkeypatch, capsys):
    mfile = tmp_path / "movements.csv"
    wfile = tmp_path / "workouts.csv"
    monkeypatch.setattr(M, "MOVEMENTS_CSV", mfile)
    monkeypatch.setattr(M, "WORKOUTS_CSV", wfile)

    M.main(["init"])
    assert mfile.exists()

    M.main(["list-movements"])  # should print no movements message
    captured = capsys.readouterr()
    assert "No movements found" in captured.out or "movement" in captured.out
