"""Dashboard API — ringkasan kelas (F-10, D6)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from repository import get_repository
from services.dashboard import map_dashboard_status

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/class/{class_id}")
def class_dashboard(class_id: str):
    """GET /dashboard/class/{id} — ringkasan kelas (F-10, D6)."""
    repo = get_repository()
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    
    students = [s for s in repo.list_students() if s.get("class_id") == class_id]
    
    # Statistik per status
    status_counts = {
        "Need Support": 0,
        "Developing": 0,
        "On Track": 0,
        "Promotion": 0,
    }
    
    student_rows = []
    for s in students:
        history = repo.list_student_assessments(s["id"])
        completed = [a for a in history if a.get("session_state") == "COMPLETED"]
        
        if completed:
            # Ambil asesmen terbaru
            completed.sort(key=lambda a: a.get("completed_at", a.get("created_at", "")), reverse=True)
            latest = completed[0]
            
            adaptive_status = latest.get("status", "STAY")
            accuracy = latest.get("accuracy", 0)
            retrieve = latest.get("retrieve", 0)
            interpret = latest.get("interpret", 0)
            reflect = latest.get("reflect", 0)
            
            dashboard_status = map_dashboard_status(
                adaptive_status, accuracy, retrieve, interpret, reflect
            )
            status_counts[dashboard_status] = status_counts.get(dashboard_status, 0) + 1
            
            # Data tren (urut waktu lama→baru)
            trend = [
                {
                    "assessment_id": a["id"],
                    "date": a.get("completed_at", a.get("created_at", "")),
                    "wcpm": a.get("wcpm", 0),
                    "accuracy": a.get("accuracy", 0),
                    "comprehension": {
                        "retrieve": a.get("retrieve", 0),
                        "interpret": a.get("interpret", 0),
                        "reflect": a.get("reflect", 0),
                    },
                }
                for a in sorted(completed, key=lambda a: a.get("completed_at", a.get("created_at", "")))
            ]
            
            student_rows.append({
                "student_id": s["id"],
                "name": s["name"],
                "grade": s["grade"],
                "wcpm": latest.get("wcpm", 0),
                "accuracy": accuracy,
                "comprehension": {
                    "retrieve": retrieve,
                    "interpret": interpret,
                    "reflect": reflect,
                },
                "status": dashboard_status,
                "adaptive_status": adaptive_status,
                "recommendation": latest.get("recommendation", ""),
                "trend": trend,
            })
        else:
            # Belum ada asesmen COMPLETED
            student_rows.append({
                "student_id": s["id"],
                "name": s["name"],
                "grade": s["grade"],
                "wcpm": None,
                "accuracy": None,
                "comprehension": None,
                "status": "Belum Ada Data",
                "adaptive_status": None,
                "recommendation": "",
                "trend": [],
            })
    
    return {
        "class_id": class_id,
        "class_name": cls.get("name", ""),
        "grade": cls.get("grade"),
        "total_students": len(students),
        "status_summary": status_counts,
        "students": student_rows,
    }
