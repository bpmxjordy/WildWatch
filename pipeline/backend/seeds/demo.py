"""Seed the database with a demo project and sample streams."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from extensions import db
from models.project import Project
from models.stream import Stream


def seed():
    app = create_app()
    with app.app_context():
        if Project.query.filter_by(name="Demo Wildlife Project").first():
            print("Demo project already exists, skipping seed.")
            return

        project = Project(
            name="Demo Wildlife Project",
            description="Sample project with wildlife camera streams for testing.",
        )
        db.session.add(project)
        db.session.flush()

        streams = [
            Stream(
                project_id=project.id,
                name="Decorah Eagles",
                source_url="https://www.youtube.com/watch?v=qdJkiEI0hHE",
                platform="youtube",
                location_name="Decorah, Iowa",
                latitude=43.30,
                longitude=-91.79,
                timezone="America/Chicago",
            ),
            Stream(
                project_id=project.id,
                name="Bear Habitat Cam",
                source_url="https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_LCTK0000070A",
                platform="jpeg",
                location_name="Grouse Mountain, BC",
                latitude=49.38,
                longitude=-123.08,
                timezone="America/Vancouver",
            ),
            Stream(
                project_id=project.id,
                name="Georgia Aquarium",
                source_url="https://relay.ozolio.com/pub.cgi?cmd=snap&oid=CID_ZMZA0000060B",
                platform="jpeg",
                location_name="Atlanta, GA",
                latitude=33.76,
                longitude=-84.39,
                timezone="America/New_York",
            ),
        ]

        for s in streams:
            db.session.add(s)

        db.session.commit()
        print(f"Seeded demo project with {len(streams)} streams.")


if __name__ == "__main__":
    seed()
