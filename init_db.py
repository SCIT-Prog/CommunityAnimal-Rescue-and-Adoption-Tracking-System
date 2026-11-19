"""Creates the MySQL database/tables from schema.sql and the first admin account.
Usage:  python init_db.py [--no-demo] [--more-demo] [--reset]   (uses DB_HOST / DB_USER / DB_PASSWORD env vars)"""
import os
from werkzeug.security import generate_password_hash

def run(conn, schema_text=None, demo=True, more=False):
    schema_text = schema_text or open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql'), encoding='utf8').read()
    cur = conn.cursor()
    for stmt in [s.strip() for s in schema_text.split(';') if s.strip()]:
        try: cur.execute(stmt)
        except Exception as e:
            if 'Duplicate key name' not in str(e) and 'already exists' not in str(e): raise
    for stmt in ['ALTER TABLE animals ADD COLUMN photo VARCHAR(255)', 'ALTER TABLE rescues ADD COLUMN photo VARCHAR(255)',
                 'ALTER TABLE users ADD COLUMN avatar VARCHAR(255)', 'ALTER TABLE users ADD COLUMN bg VARCHAR(255)', 'ALTER TABLE users ADD COLUMN bgfile VARCHAR(255)', 'ALTER TABLE users ADD COLUMN theme VARCHAR(10)',
                 "ALTER TABLE rescues ADD COLUMN source ENUM('staff','public') NOT NULL DEFAULT 'staff'",
                 "ALTER TABLE rescues ADD COLUMN case_status ENUM('new','responding','rescued','closed') NOT NULL DEFAULT 'rescued'",
                 'ALTER TABLE rescues ADD COLUMN lat DECIMAL(9,6) NULL', 'ALTER TABLE rescues ADD COLUMN lng DECIMAL(9,6) NULL', 'ALTER TABLE rescues ADD COLUMN reporter_email VARCHAR(120)',
                 'ALTER TABLE rescues ADD COLUMN assigned_to INT NULL', 'ALTER TABLE rehome_requests ADD COLUMN email VARCHAR(120)',
                 'ALTER TABLE rescues ADD COLUMN area_id INT NULL', 'ALTER TABLE adopters ADD COLUMN area_id INT NULL', 'ALTER TABLE rehome_requests ADD COLUMN area_id INT NULL', 'ALTER TABLE volunteer_applications ADD COLUMN area_id INT NULL',
                 'ALTER TABLE service_areas ADD COLUMN geojson MEDIUMTEXT NULL',
                 "ALTER TABLE service_areas MODIFY kind ENUM('city','municipality','barangay','region','country','place') NOT NULL DEFAULT 'municipality'"]:  # upgrades older databases
        try: cur.execute(stmt)
        except Exception as e:
            if 'duplicate column' not in str(e).lower(): raise
    cur.execute('select count(*) n from users'); r = cur.fetchone()
    if (r['n'] if isinstance(r, dict) else r[0]) == 0:
        for u, n, ro, p in [('admin', 'System Administrator', 'admin', 'Admin@123'), ('staff1', 'Shelter Staff', 'staff', 'Staff@123'), ('vet1', 'Dr. Veterinarian', 'vet', 'Vet@12345'), ('volunteer1', 'Field Volunteer', 'volunteer', 'Volunteer@123')]:
            cur.execute('insert into users(username,full_name,role,pw_hash) values(%s,%s,%s,%s)', (u, n, ro, generate_password_hash(p)))
    conn.commit()
    import seed_demo; seed_demo.seed_areas(conn)   # the 10 Davao del Sur places (only when the list is empty)
    if demo or more: seed_demo.seed(conn, force=more)

if __name__ == '__main__':
    import pymysql, pymysql.cursors
    c = pymysql.connect(host=os.environ.get('DB_HOST', 'localhost'), port=int(os.environ.get('DB_PORT', 3306)), user=os.environ.get('DB_USER', 'root'), password=os.environ.get('DB_PASSWORD', ''), charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    import sys, glob
    if '--reset' in sys.argv:   # wipes the whole database and starts again with the Davao del Sur samples
        name = os.environ.get('DB_NAME', 'animal_rescue')
        if input(f'This DELETES the database "{name}" and all its data. Type YES to continue: ').strip() != 'YES': sys.exit('Cancelled.')
        c.cursor().execute(f'DROP DATABASE IF EXISTS `{name}`')
        for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'demo_*.svg')): os.remove(f)
    run(c, demo='--no-demo' not in sys.argv, more='--more-demo' in sys.argv)
    print('Database ready (Davao del Sur sample data added unless --no-demo). Login: admin / Admin@123 (change it after first login).')
