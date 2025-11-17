from sqlalchemy.orm import Session
from . import models

def model_to_dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

def generate_json(db: Session):

    final_json = {
        "countdown": {},
        "champ_title": {},
        "timetable": [],
        "event_id": {},
        "lane_id": {},
        "team_id": {},
        "start_list_ind": {},
        "start_list_team": {},
        "winner_id": {},
        "new_record": {},
        "results": {},
        "qualifiers": {},
        "phase_summary": {},
        "ceremony_id": {},
        "presenters": {},
        "medal_id": {},
        "medal_list": {},
        "medal_tally": [],
        "raising_flags": {},
        "meta": {},
    }

    try:
        final_json["tournament_info"] = model_to_dict(db.query(models.TournamentInfo).first())
    except Exception as e:
        final_json["tournament_info"] = {"error": str(e)}

    try:
        medal_tally_q = db.query(
            models.MedalTally.rank,
            models.Noc.flag_url_cloud,
            models.MedalTally.noc,
            models.Noc.long_name,
            models.MedalTally.golds,
            models.MedalTally.silvers,
            models.MedalTally.bronzes,
            models.MedalTally.total
        ).join(models.Noc, models.MedalTally.noc == models.Noc.noc).order_by(models.MedalTally.rank).all()

        final_json["medal_tally"] = [
            {
                "rank": r[0],
                "flag": r[1],
                "noc": r[2],
                "name": r[3],
                "golds": r[4],
                "silvers": r[5],
                "bronzes": r[6],
                "total": r[7],
            } for r in medal_tally_q
        ]
    except Exception as e:
        final_json["medal_tally"] = {"error": str(e)}

    try:
        timetable_q = db.query(
            models.Schedule.start_time,
            models.Event.name,
            models.Schedule.phase
        ).join(models.Event, models.Schedule.event_id == models.Event.event_id).order_by(models.Schedule.start_time).all()

        final_json["timetable"] = [
            {
                "start_time": r[0].isoformat() if r[0] else None,
                "event": r[1],
                "phase": r[2]
            } for r in timetable_q
        ]
    except Exception as e:
        final_json["timetable"] = {"error": str(e)}

    try:
        start_list_q = db.query(models.StartListEntry).all()
        final_json["start_list"] = [model_to_dict(s) for s in start_list_q]
    except Exception as e:
        final_json["start_list"] = {"error": str(e)}

    try:
        results_q = db.query(models.Result).all()
        final_json["results"] = [model_to_dict(r) for r in results_q]
    except Exception as e:
        final_json["results"] = {"error": str(e)}

    try:
        medallists_q = db.query(models.Medallist).all()
        final_json["medallists"] = [model_to_dict(m) for m in medallists_q]
    except Exception as e:
        final_json["medallists"] = {"error": str(e)}

    try:
        events_q = db.query(models.Event).all()
        units_q = db.query(models.Schedule).all()
        participants_q = db.query(models.Participant).all()

        final_json["meta"] = {
            "events": [model_to_dict(e) for e in events_q],
            "units": [model_to_dict(u) for u in units_q],
            "participants": [model_to_dict(p) for p in participants_q],
        }
    except Exception as e:
        final_json["meta"] = {"error": str(e)}

    return final_json
