import os, re, csv, io, time, shutil, secrets, json, smtplib
from email.message import EmailMessage
from datetime import date, datetime, timedelta
from functools import wraps
import pymysql, pymysql.cursors
import math
from icons import icon
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort, Response
from werkzeug.security import generate_password_hash as gph, check_password_hash as cph

B = os.path.dirname(os.path.abspath(__file__))
DBCFG = dict(host=os.environ.get('DB_HOST', 'localhost'), port=int(os.environ.get('DB_PORT', 3306)), user=os.environ.get('DB_USER', 'root'),
             password=os.environ.get('DB_PASSWORD', ''), database=os.environ.get('DB_NAME', 'animal_rescue'))
KEY = os.path.join(B, 'secret.key')
if not os.environ.get('SECRET_KEY') and not os.path.exists(KEY): open(KEY, 'w').write(secrets.token_hex(32))
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or open(KEY).read()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=4))
today = lambda: date.today().isoformat()
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024
app.config['MAX_FORM_MEMORY_SIZE'] = 4 * 1024 * 1024   # the admin form can carry a big place boundary (GeoJSON)
UP = os.path.join(B, 'static', 'uploads'); os.makedirs(UP, exist_ok=True)
def save_photo(field='photo', prefix=''):
    f = request.files.get(field)
    if not f or not f.filename: return None
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''; h = f.read(12); f.seek(0)
    sig = h.startswith(b'\x89PNG') or h[:3] == b'\xff\xd8\xff' or h[:4] == b'GIF8' or (h[:4] == b'RIFF' and h[8:12] == b'WEBP')
    if ext not in ('png', 'jpg', 'jpeg', 'gif', 'webp') or not sig: flash('Photo must be a real PNG, JPG, GIF or WEBP image.', 'err'); return None
    name = prefix + secrets.token_hex(8) + '.' + ext; f.save(os.path.join(UP, name)); return name
def drop_photo(name):
    p = os.path.join(UP, os.path.basename(name or ''))
    if name and not name.startswith('demo_') and os.path.isfile(p): os.remove(p)

def db():
    if 'db' not in g: g.db = pymysql.connect(**DBCFG, charset='utf8mb4', autocommit=True, cursorclass=pymysql.cursors.DictCursor)
    return g.db
@app.teardown_appcontext
def close(e):
    d = g.pop('db', None)
    if d: d.close()
def q(sql, *a):
    with db().cursor() as c: c.execute(sql, a); return list(c.fetchall())
def q1(sql, *a): r = q(sql, *a); return r[0] if r else None
def x(sql, *a):
    with db().cursor() as c: c.execute(sql, a); return c.lastrowid
def n(sql, *a): return q1(sql, *a)['n']
def fref(prefix, i): return f'{prefix}-{int(i):04d}'
app.jinja_env.globals['fref'] = fref
app.jinja_env.globals['icon'] = icon

# ---- email (SMTP is optional; every message is also kept in the Email log) ----
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
ORG = os.environ.get('ORG_NAME', 'Animal Rescue Center')
MAIL_FILE = os.path.join(B, 'mail_settings.json')
def mail_saved():
    try: return json.load(open(MAIL_FILE, encoding='utf8'))
    except Exception: return {}
def mail_cfg():
    """Gmail settings saved by the admin (Email settings page) win; otherwise the MAIL_* environment variables are used."""
    m = mail_saved(); gm = (m.get('gmail') or '').strip(); pw = re.sub(r'\s+', '', m.get('app_password') or '')
    if gm and pw and m.get('enabled', True):
        return dict(host='smtp.gmail.com', port=587, user=gm, pw=pw, ssl=False, tls=True, sender=f"{m.get('from_name') or 'Animal Rescue'} <{gm}>", org=m.get('from_name') or ORG)
    return dict(host=os.environ.get('MAIL_HOST'), port=int(os.environ.get('MAIL_PORT', 587)), user=os.environ.get('MAIL_USER'), pw=os.environ.get('MAIL_PASSWORD'),
                sender=os.environ.get('MAIL_FROM') or os.environ.get('MAIL_USER') or 'rescue@localhost', ssl=os.environ.get('MAIL_SSL') == '1', tls=os.environ.get('MAIL_TLS', '1') == '1', org=ORG)
ORG = os.environ.get('ORG_NAME', 'Animal Rescue Center')
def smtp_send(cfg, to, subject, body):
    """Raises on failure. Used by send_mail and by the test button."""
    m = EmailMessage(); m['From'] = cfg['sender']; m['To'] = to; m['Subject'] = subject; m.set_content(body)
    with (smtplib.SMTP_SSL(cfg['host'], cfg['port'], timeout=15) if cfg['ssl'] else smtplib.SMTP(cfg['host'], cfg['port'], timeout=15)) as sm:
        if not cfg['ssl'] and cfg['tls']: sm.starttls()
        if cfg['user']: sm.login(cfg['user'], cfg['pw'] or '')
        sm.send_message(m)
def mail_hint(e):
    t = str(e)
    if isinstance(e, smtplib.SMTPAuthenticationError) or '535' in t or 'Username and Password not accepted' in t:
        return 'Gmail refused the login. Use a Google App Password (16 letters), not your normal Gmail password: Google Account > Security > turn on 2-Step Verification > App passwords.'
    if isinstance(e, (smtplib.SMTPConnectError, OSError)): return 'Could not reach smtp.gmail.com. Check the internet connection of the computer running this system.'
    return t[:200]
def send_mail(to, subject, body, ref=None):
    """Returns 'sent', 'failed', 'not_configured' or 'no_email'."""
    to = (to or '').strip()
    if not EMAIL_RE.match(to): return 'no_email'
    cfg = mail_cfg(); body = body + f"\n\n- {cfg['org']}"; st, err = 'not_configured', None
    if cfg['host']:
        try: smtp_send(cfg, to, subject, body); st = 'sent'
        except Exception as e: st, err = 'failed', mail_hint(e)[:250]
    try: x('insert into email_log(to_email,subject,body,ref,status,error) values(%s,%s,%s,%s,%s,%s)', to, subject[:200], body, ref, st, err)
    except Exception: pass
    return st
def alert_staff(subject, lines, path):
    """Email the admin's notify address when the public sends a new request (runs in the background so the visitor never waits)."""
    m = mail_saved(); to = (m.get('notify_email') or m.get('gmail') or '').strip()
    if not (m.get('alerts', True) and mail_cfg()['host'] and EMAIL_RE.match(to)): return
    link = request.host_url.rstrip('/') + path; body = '\n'.join(lines) + f'\n\nOpen it here: {link}'
    def run():
        with app.app_context(): send_mail(to, subject, body, 'ALERT')
    import threading; threading.Thread(target=run, daemon=True).start()
def notify(to, ref, headline, lines):
    """Email an applicant/reporter about a decision and tell the staff member what happened."""
    link = request.host_url + 'track?ref=' + ref
    body = headline + '\n\n' + '\n'.join(lines) + f'\n\nCheck the status of your request anytime: {link}\nReference number: {ref} (use the same phone number or email you gave us).'
    st = send_mail(to, f'[{ref}] {headline}', body, ref)
    flash({'sent': 'Email sent to the applicant.', 'not_configured': 'Email was NOT delivered because SMTP is not set up yet - the message is saved in the Email log.',
           'failed': 'Email could not be delivered (see Email log).', 'no_email': 'No email address on file - please contact them by phone.'}[st], 'err' if st == 'failed' else None)
    return st
def tomail(*vals):
    for v in vals:
        if v and EMAIL_RE.match(v.strip()): return v.strip()
    return None
def read_geo():
    try: la, ln = float(request.form.get('lat', '')), float(request.form.get('lng', ''))
    except ValueError: return None, None
    return (round(la, 6), round(ln, 6)) if -90 <= la <= 90 and -180 <= ln <= 180 and (la or ln) else (None, None)
def ago(dt):
    if not hasattr(dt, 'timestamp'): return str(dt or '')[:16]
    h = int((datetime.now() - dt).total_seconds() // 3600)
    return 'just now' if h < 1 else f'{h}h' if h < 48 else f'{h // 24}d'

# ---- constants & form helpers ----
COND = ['critical', 'injured', 'sick', 'healthy']; STATUS = ['under_care', 'available', 'adopted', 'released', 'deceased']
SEX = ['male', 'female', 'unknown']; ROLES = ['admin', 'staff', 'vet', 'volunteer']
MEDT = ['examination', 'vaccination', 'treatment', 'medication', 'follow_up']; APPST = ['pending', 'approved', 'rejected', 'completed', 'cancelled']
opts = lambda L: [(v, v.replace('_', ' ').title()) for v in L]
def F(nm, l, t='text', o=None, r=False): return dict(n=nm, l=l, t=t, o=o, r=r)
RESCUE_F = [F('rescue_date', 'Rescue date', 'date', r=True), F('location', 'Rescue location', r=True), F('species', 'Animal type / species', r=True), F('description', 'Animal details (breed, color, size, markings)', 'textarea'),
            F('animal_condition', 'Condition', 'select', opts(COND), True), F('details', 'Circumstances / condition notes', 'textarea'), F('reporter_name', 'Reporter name'), F('reporter_contact', 'Reporter contact'), F('reporter_email', 'Reporter email (for status updates)', 'email'), F('photo', 'Photo of the animal (PNG/JPG/GIF/WEBP, max 6 MB)', 'file')]
ANIMAL_F = [F('name', 'Name', r=True), F('species', 'Species', r=True), F('breed', 'Breed'), F('sex', 'Sex', 'select', opts(SEX)), F('age_years', 'Age (years)', 'number'), F('color', 'Color'),
            F('intake_date', 'Intake date', 'date', r=True), F('status', 'Current status', 'select', opts(STATUS), True), F('medical_history', 'Medical history', 'textarea'), F('notes', 'Notes', 'textarea'), F('photo', 'Photo (PNG/JPG/GIF/WEBP, max 6 MB)', 'file')]
MED_F = [F('record_type', 'Record type', 'select', opts(MEDT), True), F('record_date', 'Date', 'date', r=True), F('details', 'Details / findings', 'textarea', r=True), F('medication', 'Medication'), F('dosage', 'Dosage'), F('vet_name', 'Veterinarian / staff'), F('followup_date', 'Follow-up appointment date', 'date')]
ADOPTER_F = [F('full_name', 'Full name', r=True), F('email', 'Email (we send updates here)', 'email'), F('phone', 'Phone', 'tel', r=True), F('address', 'Address'), F('household_notes', 'Household, pets & experience notes', 'textarea')]

def read(fs):
    v = {}
    for f in fs:
        if f['t'] == 'file': continue
        s = request.form.get(f['n'], '').strip() or None
        if s and f['o'] and s not in [o[0] for o in f['o']]: s = None
        if s and f['t'] != 'number': s = s[:5000] if f['t'] == 'textarea' else s[:200]
        if s and f['t'] == 'number':
            try: s = float(s)
            except ValueError: s = None
        v[f['n']] = s
    return v
def missing(fs, v): return [f['l'] for f in fs if f['r'] and f['t'] != 'file' and v[f['n']] is None]
def ins(t, v): return x(f"insert into {t}({','.join(v)}) values({','.join(['%s'] * len(v))})", *v.values())
def upd(t, i, v): x(f"update {t} set {','.join(k + '=%s' for k in v)} where id=%s", *v.values(), i)
def show(v): return '—' if v is None or v == '' else str(v).replace('_', ' ')
def R(cells, link=None, actions=()): return dict(cells=[show(c) for c in cells], link=link, actions=actions)
def page(title, fs, vals, back, **k): return render_template('form.html', title=title, fs=fs, vals=vals, back=back, **k)

# ---- security ----
@app.before_request
def guard():
    if request.endpoint == 'static': return
    session.permanent = True
    if 'uid' in session:
        u = q1('select active from users where id=%s', session['uid'])
        if not u or not u['active']: session.clear()
    if request.method == 'POST' and not secrets.compare_digest(request.form.get('_csrf', ''), session.get('csrf', 'x')): abort(400)
PRESETS = [('meadow', 'Meadow'), ('sunset', 'Sunset'), ('ocean', 'Ocean'), ('night', 'Night sky'), ('bones', 'Bones & bowls')]; PATTERNS = ('bones',)
def bg_info():
    v = session.get('bg'); f = session.get('bgfile')
    if v == 'upload' and f and os.path.isfile(os.path.join(UP, os.path.basename(f))): return url_for('static', filename='uploads/' + os.path.basename(f)), 'scene'
    if v and v.startswith('preset:') and v[7:] in dict(PRESETS): return url_for('static', filename=f'img/bg/{v[7:]}.svg'), ('pattern' if v[7:] in PATTERNS else 'scene')
    return None, ''
def nav_counts():
    try:
        soon = (date.today() + timedelta(days=7)).isoformat()
        nv = dict(newrep=n("select count(*) n from rescues where case_status='new'"), pending=n("select count(*) n from applications where status='pending'"),
                  rehome=n("select count(*) n from rehome_requests where status='pending'"), vol=n("select count(*) n from volunteer_applications where status='pending'"),
                  pledge=n("select count(*) n from pledges where status='pending'"),
                  due=n('select count(*) n from medical_records where followup_date is not null and followup_done=0 and followup_date<=%s', soon))
        nv['queue'] = nv['newrep'] + nv['rehome'] + nv['vol'] + nv['pledge'] + nv['pending']
        return nv
    except Exception: return {}
@app.context_processor
def ctx():
    if 'csrf' not in session: session['csrf'] = secrets.token_hex(16)
    bgu, bgk = bg_info()
    nav = nav_counts() if session.get('uid') else {}
    return dict(csrf=session['csrf'], S=session, bgu=bgu, bgk=bgk, presets=PRESETS, nav=nav)
def need(*roles):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if 'uid' not in session: return redirect(url_for('login'))
            if roles and session['role'] not in roles: abort(403)
            return f(*a, **k)
        return w
    return deco
STAFF = ('admin', 'staff'); CARE = ('admin', 'staff', 'vet')

@app.route('/')
def home():
    st = dict(avail=n("select count(*) n from animals where status='available'"), adopted=n("select count(*) n from applications where status='completed'"), care=n("select count(*) n from animals where status='under_care'"))
    return render_template('home.html', pets=q("select * from animals where status='available' order by id desc limit 12"), st=st, needs=[i for i in NEEDS if i['key'] in ('food', 'bed', 'leash', 'vet')])
@app.route('/pets/<int:aid>', methods=['GET', 'POST'])
def pet_public(aid):
    a = q1("select * from animals where id=%s and status='available'", aid) or abort(404); rows = areas(); fs = with_area(ADOPTER_F, 'address', rows)
    if request.method == 'POST':
        if request.form.get('website'): abort(400)
        v = read(fs); m = missing(fs, v)
        if not rows: flash(CLOSED_MSG, 'err')
        elif m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif (e := area_error(v['area_id'], rows=rows)): flash(e, 'err')
        else:
            v['address'] = place_text(v['address'], v['area_id'], rows); v['area_id'] = int(v['area_id'])
            ex = q1('select id from adopters where phone=%s and full_name=%s', v['phone'], v['full_name']); pid = ex['id'] if ex else ins('adopters', v)
            apid = ins('applications', dict(animal_id=aid, adopter_id=pid, notes='Submitted via public website.'))
            alert_staff(f"New adoption application {fref('AP', apid)} for {a['name']}", [f"{v['full_name']} ({v['phone']}) applied to adopt {a['name']}."], url_for('applications', status='pending'))
            return done('Application sent - thank you!', fref('AP', apid), f"Our staff will review your application to adopt {a['name']}. We will email or call you once it is approved.", url_for('pets_public'), 'See more pets')
    return render_template('pet_public.html', a=a, fs=fs, svc=area_names(rows), closed=not rows)
@app.route('/login')
def login_old(): return redirect(url_for('login'))
@app.route('/staff/login', methods=['GET', 'POST'])
def login():
    if 'uid' in session and request.method == 'GET': return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if too_many('login', 12, 600): flash('Too many sign-in attempts. Please wait a few minutes.', 'err'); return render_template('staff_login.html', title='Staff sign in')
        u = q1('select * from users where username=%s', request.form['username'].strip())
        if u and u['active'] and cph(u['pw_hash'], request.form['password']):
            keep = {k: session[k] for k in ('theme', 'bg') if k in session}; session.clear(); session.update(keep)
            session.update(uid=u['id'], role=u['role'], name=u['full_name'], csrf=secrets.token_hex(16), avatar=u.get('avatar'), bgfile=u.get('bgfile'))
            if u.get('theme'): session['theme'] = u['theme']
            if u.get('bg'): session['bg'] = u['bg']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'err')
    return render_template('staff_login.html', title='Staff sign in')
@app.route('/logout', methods=['POST'])
def logout(): keep = {k: session[k] for k in ('theme',) if k in session}; session.clear(); session.update(keep); return redirect(url_for('home'))
@app.route('/password', methods=['GET', 'POST'])
@need()
def password():
    fs = [F('old', 'Current password', 'password', r=True), F('new', 'New password (8+ characters)', 'password', r=True), F('new2', 'Confirm new password', 'password', r=True)]
    if request.method == 'POST':
        u = q1('select * from users where id=%s', session['uid']); f = request.form
        if not cph(u['pw_hash'], f['old']): flash('Current password is wrong.', 'err')
        elif len(f['new']) < 8 or f['new'] != f['new2']: flash('New password must be 8+ characters and match.', 'err')
        else: x('update users set pw_hash=%s where id=%s', gph(f['new']), u['id']); flash('Password updated.'); return redirect(url_for('dashboard'))
    return page('Change password', fs, {}, url_for('dashboard'))

# ---- public: found-pet report, rehome form, pet needs ----
HITS = {}
def too_many(tag, mx=6, per=3600):
    k = (request.remote_addr, tag); now = time.time(); L = [t for t in HITS.get(k, []) if now - t < per]; full = len(L) >= mx
    if not full: L.append(now)
    HITS[k] = L; return full

# ---- service areas: the places the admin allows for public requests/reports ----
CLOSED_MSG = 'We are not accepting online requests right now. Please contact the rescue center directly.'
AREA_KINDS = [('country', 'Country'), ('region', 'Region / province'), ('city', 'City'), ('municipality', 'Municipality'), ('barangay', 'Barangay'), ('place', 'Other place (circle)')]
KIND_ORDER = "field(kind,'country','region','city','municipality','barangay','place')"
def areas(active=True): return q('select * from service_areas' + (' where active=1' if active else '') + " order by " + KIND_ORDER + ", name")
def with_area(fs, before='address', rows=None):
    """Adds the required 'place' dropdown (only the places the admin switched on) before the given field."""
    f = F('area_id', 'Place we serve', 'select', [(str(a['id']), a['name']) for a in (rows if rows is not None else areas())], True)
    i = next((k for k, g in enumerate(fs) if g['n'] == before), len(fs)); return fs[:i] + [f] + fs[i:]
def km(a, b, c, d):
    p = math.pi / 180; h = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2; return 12742 * math.asin(math.sqrt(h))
def area_names(rows=None): return ', '.join(a['name'] for a in (rows if rows is not None else areas()))
def _ring(la, ln, r):
    """Ray casting: is the point inside this ring of [lng, lat] pairs?"""
    c = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi, xj, yj = r[i][0], r[i][1], r[j][0], r[j][1]
        if (yi > la) != (yj > la) and ln < (xj - xi) * (la - yi) / (yj - yi) + xi: c = not c
        j = i
    return c
def in_geo(g, la, ln):
    """Point inside a GeoJSON Polygon / MultiPolygon (holes respected)."""
    polys = [g['coordinates']] if g.get('type') == 'Polygon' else g['coordinates'] if g.get('type') == 'MultiPolygon' else []
    return any(_ring(la, ln, p[0]) and not any(_ring(la, ln, h) for h in p[1:]) for p in polys)
def clean_geojson(raw):
    """Validates a boundary sent by the admin's browser. Returns compact JSON text, or None if it is not a usable Polygon/MultiPolygon."""
    try:
        g = json.loads(raw)
        if g.get('type') == 'Feature': g = g.get('geometry') or {}
        t = g.get('type'); polys = [g['coordinates']] if t == 'Polygon' else g['coordinates'] if t == 'MultiPolygon' else None
        if not polys: return None
        out = []
        for p in polys:
            rings = []
            for r in p:
                pts = []
                for c in r:
                    lng, lat = round(float(c[0]), 5), round(float(c[1]), 5)
                    if not (-180 <= lng <= 180 and -90 <= lat <= 90): return None
                    if not pts or pts[-1] != [lng, lat]: pts.append([lng, lat])
                if len(pts) >= 4: rings.append(pts)
                elif not rings: break          # outer ring unusable: skip this polygon
            if rings: out.append(rings)
        if not out: return None
        res = json.dumps({'type': 'Polygon', 'coordinates': out[0]} if len(out) == 1 else {'type': 'MultiPolygon', 'coordinates': out}, separators=(',', ':'))
        return res if len(res) <= 2_000_000 else None
    except (ValueError, TypeError, KeyError, IndexError, AttributeError): return None
def area_geo(a):
    try: return json.loads(a['geojson']) if a.get('geojson') else None
    except ValueError: return None
def area_hit(a, la, ln):
    g = area_geo(a)
    return in_geo(g, la, ln) if g else km(la, ln, float(a['lat']), float(a['lng'])) <= float(a['radius_km'])
def area_error(aid, la=None, ln=None, rows=None):
    """None when the request is allowed, otherwise the message shown to the person."""
    rows = rows if rows is not None else areas()
    if not rows: return CLOSED_MSG
    if not any(str(a['id']) == str(aid) for a in rows): return 'Please choose one of the places we serve: ' + area_names(rows) + '.'
    if la is not None and ln is not None and not any(area_hit(a, la, ln) for a in rows):
        return 'The pin you dropped is outside the places we serve (' + area_names(rows) + '). Please drop it inside the highlighted area on the map.'
    return None
def place_text(txt, aid, rows, la=None, ln=None):
    name = next((a['name'] for a in rows if str(a['id']) == str(aid)), '')
    txt = (txt or '').strip() or (f'Map pin {la:.5f}, {ln:.5f}' if la is not None else '')
    return (txt if name.lower() in txt.lower() else f'{txt}, {name}' if txt else name)[:200]
def area_cfg(restrict=True, rows=None):
    rows = rows if rows is not None else areas(); c = [[float(a['lat']), float(a['lng'])] for a in rows]
    return dict(restrict=restrict, center=[sum(p[0] for p in c) / len(c), sum(p[1] for p in c) / len(c)] if c else None,   # no places yet = world map
                areas=[dict(n=a['name'], lat=float(a['lat']), lng=float(a['lng']), r=float(a['radius_km']), on=bool(a['active']), **({'g': area_geo(a)} if area_geo(a) else {})) for a in rows])
CASE = ['new', 'responding', 'rescued', 'closed']
SPECIES_HINT = ['Dog', 'Cat', 'Rabbit', 'Bird', 'Turtle', 'Other']
def FD(nm, l, hints, r=False): f = F(nm, l, r=r); f['dl'] = hints; return f
FOUND_COND = [('critical', 'Critical - badly hurt / cannot move'), ('injured', 'Injured / bleeding'), ('sick', 'Looks sick or weak'), ('healthy', 'Looks healthy / just lost')]
FOUND_F = [F('photo', 'Photo of the animal (take a picture or choose one)', 'file', r=True), FD('species', 'What animal is it?', SPECIES_HINT, True), F('animal_condition', 'How does it look?', 'select', FOUND_COND, True), F('location', 'Where is it? (street, landmark, barangay) - or drop a pin on the map below'),
           F('description', 'What does it look like? (color, size, collar, markings)', 'textarea'), F('details', 'Anything else we should know? (aggressive, with puppies, in traffic...)', 'textarea'), F('reporter_name', 'Your name (optional)'), F('reporter_contact', 'Your phone number (so the rescuers can reach you)', r=True), F('reporter_email', 'Your email (optional - we will email you updates)', 'email')]
REHOME_F = [F('photo', 'Photo of your pet', 'file'), F('owner_name', 'Your full name', r=True), F('contact', 'Your phone number', r=True), F('email', 'Your email (we will email you when we decide)', 'email'), F('address', 'Your address'), F('pet_name', "Your pet's name", r=True), FD('species', 'Animal', SPECIES_HINT, True), F('breed', 'Breed'), F('sex', 'Sex', 'select', opts(SEX)),
            F('age_years', 'Age (years)', 'number'), F('color', 'Color'), F('reason', 'Why do you want to give your pet up for adoption?', 'textarea', r=True), F('health_notes', 'Health, vaccines, temperament, habits, favorite food', 'textarea')]
@app.route('/report-found', methods=['GET', 'POST'])
def found():
    v = {}; rows = areas(); fs = with_area(FOUND_F, 'location', rows)
    if request.method == 'POST':
        if request.form.get('website'): abort(400)
        v = read(fs); m = missing(fs, v); ph = request.files.get('photo'); la, ln = read_geo()
        if not m and not v['location'] and la is None: m = ['Location (type it or drop a pin on the map)']
        if not rows: flash(CLOSED_MSG, 'err')
        elif m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif la is None: flash('Please drop a pin on the map, inside the places we serve. A report without a valid pin cannot be sent.', 'err')
        elif (e := area_error(v['area_id'], la, ln, rows)): flash(e, 'err')
        elif not ph or not ph.filename: flash('Please take or upload a photo of the animal.', 'err')
        elif too_many('found'): flash('Too many reports from this device. Please call the rescue center directly.', 'err')
        else:
            p = save_photo()
            if p: v['location'] = place_text(v['location'], v['area_id'], rows, la, ln); v['area_id'] = int(v['area_id']); session['last_report'] = ins('rescues', dict(v, rescue_date=today(), source='public', case_status='new', photo=p, lat=la, lng=ln)); alert_staff(f"New rescue report R-{session['last_report']:04d}", [f"{v.get('animal_condition', '')} {v.get('species', '')} at {v.get('location', '')}"], url_for('rescue_view', rid=session['last_report'])); return redirect(url_for('found_thanks'))
    return render_template('found.html', title='I found a pet', fs=fs, vals=v, geo=True, svc=area_names(rows), closed=not rows, svc_cfg=area_cfg(True, rows))
@app.route('/report-found/thanks')
def found_thanks():
    rid = session.pop('last_report', None)
    if not rid: return redirect(url_for('found'))
    return render_template('thanks.html', title='Report sent', h='Report sent - thank you!', ref=f'R-{rid:04d}', again=url_for('found'), againl='Report another animal',
                           msg='The rescue center can already see your report and photo on their dashboard. A rescuer will respond as soon as possible. If the animal is in danger, please keep a safe distance and stay nearby if you can.')
@app.route('/rehome', methods=['GET', 'POST'])
def rehome():
    v = {}; rows = areas(); fs = with_area(REHOME_F, 'address', rows)
    if request.method == 'POST':
        if request.form.get('website'): abort(400)
        v = read(fs); m = missing(fs, v)
        if not rows: flash(CLOSED_MSG, 'err')
        elif m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif (e := area_error(v['area_id'], rows=rows)): flash(e, 'err')
        elif too_many('rehome'): flash('Too many requests from this device. Please contact the center directly.', 'err')
        else: v['address'] = place_text(v['address'], v['area_id'], rows); v['area_id'] = int(v['area_id']); p = save_photo(); session['last_rehome'] = ins('rehome_requests', dict(v, photo=p)); alert_staff(f"New rehome request RH-{session['last_rehome']:04d}", [f"{v.get('owner_name', '')} wants to rehome {v.get('pet_name', '')}."], url_for('requests_list')); return redirect(url_for('rehome_thanks'))
    return render_template('rehome.html', title='Rehome my pet', fs=fs, vals=v, svc=area_names(rows), closed=not rows)
@app.route('/rehome/thanks')
def rehome_thanks():
    rid = session.pop('last_rehome', None)
    if not rid: return redirect(url_for('rehome'))
    return render_template('thanks.html', title='Request sent', h='Request received', ref=f'RH-{rid:04d}', again=url_for('home'), againl='Back to home',
                           msg='Our staff will review your request and contact you to arrange the handover. Thank you for making sure your pet finds a safe, loving home.')
NEEDS = [dict(key='food', title='Good food & treats', who=('dog', 'cat', 'rabbit', 'bird'), text='Age-appropriate food, measured meals and training treats. Birds need seed or pellets plus fresh fruit and veggies.'),
         dict(key='water', title='Fresh water, always', who=('dog', 'cat', 'rabbit', 'bird'), text='Clean the bowl or bottle daily and refill with fresh water, especially on hot days.'),
         dict(key='bed', title='Cozy bed or shelter', who=('dog', 'cat', 'rabbit'), text='A dry, quiet, shaded place to sleep away from drafts and rain.'),
         dict(key='leash', title='Collar, ID tag & leash', who=('dog', 'cat'), text='A snug collar with your phone number helps a lost pet find its way home. Walk dogs on a leash.'),
         dict(key='carrier', title='Carrier or crate', who=('dog', 'cat', 'rabbit', 'bird'), text='Safe transport for vet visits and travel. Let your pet explore it at home first.'),
         dict(key='litter', title='Litter box', who=('cat', 'rabbit'), text='One box per pet, kept in a quiet corner and scooped every day.'),
         dict(key='vet', title='Vaccines & vet checkups', who=('dog', 'cat', 'rabbit', 'bird'), text='Yearly checkups, vaccinations, deworming and spay/neuter keep pets healthy and prevent stray litters.'),
         dict(key='groom', title='Grooming & hygiene', who=('dog', 'cat', 'rabbit'), text='Regular brushing, baths when needed, nail trims and teeth care.'),
         dict(key='toys', title='Toys & exercise', who=('dog', 'cat', 'rabbit', 'bird'), text='Balls, chew toys, scratchers and daily play keep pets happy and stop boredom.'),
         dict(key='cage', title='Cage, hutch & perches', who=('rabbit', 'bird'), text='A roomy, clean cage with perches or a hiding spot. Let them out for safe supervised time.'),
         dict(key='hay', title='Hay & fresh greens', who=('rabbit',), text='Unlimited hay keeps rabbit teeth and digestion healthy. Add leafy greens and a little carrot.')]
KINDS = [('', 'All pets'), ('dog', 'Dogs'), ('cat', 'Cats'), ('rabbit', 'Rabbits'), ('bird', 'Birds')]
@app.route('/needs')
def needs():
    s = request.args.get('s', ''); s = s if s in dict(KINDS) else ''
    return render_template('needs.html', title='Pet needs & supplies', items=[i for i in NEEDS if not s or s in i['who']], s=s, kinds=KINDS)


# ---- live notifications (the bell polls this) ----
@app.route('/staff/notify.json')
@need('admin', 'staff', 'vet')
def notify_json():
    role = session['role']; it = []
    def add(k, kind, title, text, url, at): it.append(dict(k=k, kind=kind, title=title, text=text, url=url, at=str(at or '')[:19], ago=ago(at) if at else ''))
    for r in q("select id,species,location,animal_condition,created_at from rescues where case_status='new' order by id desc limit 6"):
        add(f"R{r['id']}", 'rescue', f"New rescue report {fref('R', r['id'])}", f"{r['animal_condition']} {r['species']} at {r['location']}", url_for('rescue_view', rid=r['id']), r['created_at'])
    if role in ('admin', 'staff'):
        for r in q("select a.id,a.applied_at,an.name aname,d.full_name from applications a join animals an on an.id=a.animal_id join adopters d on d.id=a.adopter_id where a.status='pending' order by a.id desc limit 6"):
            add(f"AP{r['id']}", 'adoption', f"Adoption application {fref('AP', r['id'])}", f"{r['full_name']} wants to adopt {r['aname']}", url_for('applications', status='pending'), r['applied_at'])
        for r in q("select id,pet_name,owner_name,created_at from rehome_requests where status='pending' order by id desc limit 4"):
            add(f"RH{r['id']}", 'rehome', f"Rehome request {fref('RH', r['id'])}", f"{r['owner_name']} asks to rehome {r['pet_name']}", url_for('requests_list'), r['created_at'])
        for r in q("select id,full_name,kind,created_at from volunteer_applications where status='pending' order by id desc limit 4"):
            add(f"VF{r['id']}", 'volunteer', f"Volunteer / foster {fref('VF', r['id'])}", f"{r['full_name']} applied ({r['kind']})", url_for('volunteers'), r['created_at'])
        for r in q("select p.id,p.qty,p.pledger_name,p.created_at,s.name item,s.unit from pledges p join supplies s on s.id=p.supply_id where p.status='pending' order by p.id desc limit 4"):
            add(f"PL{r['id']}", 'pledge', f"Supply pledge {fref('PL', r['id'])}", f"{r['pledger_name']}: {r['qty']} {r['unit']} {r['item']}", url_for('pledges'), r['created_at'])
    it.sort(key=lambda d: d['at'], reverse=True)
    nv = nav_counts()
    return Response(json.dumps(dict(total=nv.get('queue', 0), items=it[:10], queue=url_for('queue'))), mimetype='application/json', headers={'Cache-Control': 'no-store'})

# ---- Gmail / SMTP settings (admin) ----
@app.route('/staff/email-settings', methods=['GET', 'POST'])
@need('admin')
def mail_settings():
    m = mail_saved()
    if request.method == 'POST':
        f = request.form; gm = f.get('gmail', '').strip(); pw = re.sub(r'\s+', '', f.get('app_password', '')) or re.sub(r'\s+', '', m.get('app_password', ''))
        if gm and not EMAIL_RE.match(gm): flash('Please enter a valid Gmail address.', 'err')
        else:
            m = dict(gmail=gm, app_password=pw, from_name=f.get('from_name', '').strip()[:80] or 'Animal Rescue', notify_email=f.get('notify_email', '').strip(), alerts=bool(f.get('alerts')), enabled=True)
            if m['notify_email'] and not EMAIL_RE.match(m['notify_email']): flash('The alert email address is not valid.', 'err')
            else:
                with open(MAIL_FILE, 'w', encoding='utf8') as fh: json.dump(m, fh, indent=1)
                try: os.chmod(MAIL_FILE, 0o600)
                except Exception: pass
                if f.get('act') == 'test':
                    to = f.get('test_to', '').strip() or gm
                    if not EMAIL_RE.match(to): flash('Enter an email address to send the test to.', 'err')
                    elif not (gm and pw): flash('Enter the Gmail address and the App Password first.', 'err')
                    else:
                        try: smtp_send(mail_cfg(), to, 'Test email from the Animal Rescue System', 'Success! Your Gmail settings work. The system can now email applicants and alert staff.'); flash(f'Test email sent to {to}. Check the inbox (and Spam).')
                        except Exception as e: flash('Test failed: ' + mail_hint(e), 'err')
                else: flash('Email settings saved.')
                return redirect(url_for('mail_settings'))
    return render_template('mail_settings.html', title='Email settings', m=m, has_pw=bool(m.get('app_password')), live=mail_cfg()['host'])

# ---- appearance: dark mode, background, profile ----
@app.route('/theme', methods=['POST'])
def set_theme():
    t = request.form.get('theme')
    if t in ('light', 'dark', 'auto'):
        session['theme'] = t
        if 'uid' in session: x('update users set theme=%s where id=%s', t, session['uid'])
    return '', 204
@app.route('/background', methods=['POST'])
def set_bg():
    c = request.form.get('bg', ''); ok = c == 'default' or (c.startswith('preset:') and c[7:] in dict(PRESETS)) or (c == 'upload' and session.get('bgfile'))
    if ok:
        if c == 'default': session.pop('bg', None)
        else: session['bg'] = c
        if 'uid' in session: x('update users set bg=%s where id=%s', None if c == 'default' else c, session['uid'])
    ref = request.referrer or ''
    return redirect(ref if ref.startswith(request.host_url) else url_for('home'))
@app.route('/profile', methods=['GET', 'POST'])
@need()
def profile():
    u = q1('select * from users where id=%s', session['uid'])
    if request.method == 'POST':
        name = (request.form.get('full_name') or '').strip()[:100]
        if not name: flash('Please enter your name.', 'err')
        else:
            v = dict(full_name=name); th = request.form.get('theme'); v['theme'] = th if th in ('auto', 'light', 'dark') else 'auto'
            av = save_photo('avatar', 'av_')
            if av: drop_photo(u['avatar']); v['avatar'] = av
            elif request.form.get('rm_avatar'): drop_photo(u['avatar']); v['avatar'] = None
            bf = save_photo('bgfile', 'bg_'); ch = request.form.get('bg_choice', 'default')
            if bf: drop_photo(u['bgfile']); v['bgfile'] = bf; ch = 'upload'
            elif request.form.get('rm_bgfile'): drop_photo(u['bgfile']); v['bgfile'] = None; ch = 'default' if ch == 'upload' else ch
            if ch == 'upload' and not (v.get('bgfile') or (u['bgfile'] and 'bgfile' not in v)): ch = 'default'
            v['bg'] = None if ch == 'default' else ch if (ch == 'upload' or (ch.startswith('preset:') and ch[7:] in dict(PRESETS))) else None
            upd('users', u['id'], v)
            session['name'] = name; session['theme'] = v['theme']; session['avatar'] = v.get('avatar', u['avatar']); session['bgfile'] = v.get('bgfile', u['bgfile'])
            if v['bg']: session['bg'] = v['bg']
            else: session.pop('bg', None)
            flash('Profile updated.'); return redirect(url_for('profile'))
    return render_template('profile.html', title='My profile', u=u)

# ---- rehome requests (staff) ----
@app.route('/requests')
@need(*STAFF)
def requests_list():
    return render_template('requests.html', title='Rehome requests', items=q("select * from rehome_requests order by status='pending' desc, id desc limit 200"))
@app.route('/requests/<int:rid>/<act>', methods=['POST'])
@need(*STAFF)
def request_act(rid, act):
    r = q1('select * from rehome_requests where id=%s', rid) or abort(404)
    if act not in ('accept', 'decline') or r['status'] != 'pending': flash('That request was already handled.', 'err'); return redirect(url_for('requests_list'))
    to = tomail(r.get('email'), r['contact'])
    if act == 'decline':
        x("update rehome_requests set status='declined' where id=%s", rid); flash('Request declined.')
        notify(to, fref('RH', rid), 'Update on your rehome request', [f"Hello {r['owner_name']},", f"Thank you for contacting us about {r['pet_name']}. Unfortunately we are unable to take {r['pet_name']} in right now.", 'Please call us and we will gladly suggest other options.']); return redirect(url_for('requests_list'))
    ph = None; src = os.path.join(UP, os.path.basename(r['photo'] or ''))
    if r['photo'] and os.path.isfile(src): ph = 'rh_' + secrets.token_hex(6) + os.path.splitext(src)[1]; shutil.copy(src, os.path.join(UP, ph))
    aid = ins('animals', dict(name=r['pet_name'], species=r['species'], breed=r['breed'], sex=r['sex'] or 'unknown', age_years=r['age_years'], color=r['color'], intake_date=today(), status='under_care',
                              medical_history=r['health_notes'], notes=f"Owner surrender from {r['owner_name']} ({r['contact']}). Reason: {r['reason']}", photo=ph))
    x("update rehome_requests set status='accepted', animal_id=%s where id=%s", aid, rid); flash('Request accepted - animal profile created. Please review the details and set the status to Available when ready.')
    notify(to, fref('RH', rid), 'Your rehome request was approved', [f"Hello {r['owner_name']},", f"Good news! We approved your request to rehome {r['pet_name']}.", 'Our staff will contact you to arrange the handover. Please keep your phone nearby and prepare any vaccine records.']); return redirect(url_for('animal_edit', aid=aid))

# ---- dashboard ----
@app.route('/dashboard')
@need()
def dashboard():
    soon = (date.today() + timedelta(days=7)).isoformat()
    st = dict(rescued=n('select count(*) n from rescues'), care=n("select count(*) n from animals where status='under_care'"), avail=n("select count(*) n from animals where status='available'"),
              adopted=n("select count(*) n from applications where status='completed'"), pending=n("select count(*) n from applications where status='pending'"),
              newrep=n("select count(*) n from rescues where case_status='new'"), rehome=n("select count(*) n from rehome_requests where status='pending'"), vol=n("select count(*) n from volunteer_applications where status='pending'"), pledge=n("select count(*) n from pledges where status='pending'"), mine=n("select count(*) n from rescues where assigned_to=%s and case_status in ('new','responding')", session['uid']))
    due = q('select m.animal_id,m.followup_date,a.name from medical_records m join animals a on a.id=m.animal_id where m.followup_date is not null and m.followup_done=0 and m.followup_date<=%s order by m.followup_date limit 8', soon)
    def bars(rows, k):
        mx = max([r['n'] for r in rows] or [1]); return [dict(label=str(r[k]).replace('_', ' '), n=r['n'], pct=round(100 * r['n'] / mx)) for r in rows]
    by_m = {r['m']: r['n'] for r in q('select substr(rescue_date,1,7) m, count(*) n from rescues group by substr(rescue_date,1,7)')}
    trend = line_chart(month_series(by_m, 6))
    stat_rows = q('select status, count(*) n from animals group by status order by n desc')
    this_m, last_m = trend['vals'][-1], (trend['vals'][-2] if len(trend['vals']) > 1 else 0)
    return render_template('dashboard.html', st=st, due=due, today=today(), recent=q('select * from rescues order by id desc limit 6'), newest=q('select * from animals order by id desc limit 6'),
                           species=bars(q('select species, count(*) n from animals group by species order by n desc limit 8'), 'species'), by_status=bars(stat_rows, 'status'),
                           trend=trend, donut=donut([dict(label=str(r['status']).replace('_', ' '), n=r['n']) for r in stat_rows]), this_m=this_m, last_m=last_m, title='Dashboard')

# ---- chart helpers (server-side SVG numbers) ----
def month_series(by_m, k=6):
    y, m = date.today().year, date.today().month; out = []
    for _ in range(k):
        out.append((f'{y:04d}-{m:02d}', by_m.get(f'{y:04d}-{m:02d}', 0))); m -= 1
        if m == 0: y, m = y - 1, 12
    return list(reversed(out))
def line_chart(series, W=640, H=240, L=40, R=18, T=16, B=34):
    vals = [v for _, v in series]; top = max(vals + [1]); step = 1 if top <= 5 else (2 if top <= 10 else (5 if top <= 25 else 10)); ymax = int(math.ceil(top / step) * step)
    iw, ih = W - L - R, H - T - B; k = len(series)
    pts = [(L + (iw * i / (k - 1) if k > 1 else iw / 2), T + ih - ih * v / ymax) for i, v in enumerate(vals)]
    d = f'M{pts[0][0]:.1f},{pts[0][1]:.1f}'
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]): d += f' C{(x0 + x1) / 2:.1f},{y0:.1f} {(x0 + x1) / 2:.1f},{y1:.1f} {x1:.1f},{y1:.1f}'
    area = d + f' L{pts[-1][0]:.1f},{T + ih:.1f} L{pts[0][0]:.1f},{T + ih:.1f} Z'
    ticks = [dict(y=round(T + ih - ih * t / ymax, 1), v=t) for t in range(0, ymax + 1, max(1, ymax // 4 if ymax >= 4 else 1))]
    labs = [dict(x=round(p[0], 1), t=datetime.strptime(m, '%Y-%m').strftime('%b'), y=m[:4], v=v, py=round(p[1], 1)) for p, (m, v) in zip(pts, series)]
    return dict(W=W, H=H, L=L, R=R, T=T, B=B, d=d, area=area, ticks=ticks, labs=labs, vals=vals, total=sum(vals), base=T + ih)
def donut(rows, r=42):
    tot = sum(x['n'] for x in rows); C = 2 * math.pi * r; off = 0; segs = []
    for i, x in enumerate(rows):
        L = C * x['n'] / (tot or 1); gap = 2.2 if len(rows) > 1 else 0
        segs.append(dict(label=x['label'], n=x['n'], pct=round(100 * x['n'] / (tot or 1)), dash=f'{max(L - gap, .1):.2f} {C - max(L - gap, .1):.2f}', off=f'{-off:.2f}', k=i % 6)); off += L
    return dict(total=tot, segs=segs, r=r)

# ---- rescue incidents ----
@app.route('/rescues')
@need()
def rescues():
    a = request.args; sql = 'select * from rescues where 1=1'; p = []
    sql = 'select r.*,u.full_name who from rescues r left join users u on u.id=r.assigned_to where 1=1'
    if a.get('q'): sql += ' and (r.location like %s or r.species like %s or r.description like %s or r.reporter_name like %s)'; p += [f"%{a['q'][:60]}%"] * 4
    if a.get('c'): sql += ' and r.animal_condition=%s'; p.append(a['c'])
    if a.get('cs'): sql += ' and r.case_status=%s'; p.append(a['cs'])
    if a.get('src') in ('public', 'staff'): sql += ' and r.source=%s'; p.append(a['src'])
    if a.get('mine'): sql += ' and r.assigned_to=%s'; p.append(session['uid'])
    rows = [R([fref('R', r['id']), r['rescue_date'], r['location'], r['species'], r['animal_condition'], 'Public report' if r['source'] == 'public' else 'Staff', r['case_status'], r['who'] or 'Unassigned'], url_for('rescue_view', rid=r['id'])) for r in q(sql + " order by r.case_status='new' desc, r.rescue_date desc, r.id desc limit 300", *p)]
    return render_template('table.html', title='Rescue incident reports', cols=['Report', 'Date', 'Location', 'Animal', 'Condition', 'Source', 'Case', 'Handled by'], rows=rows, add=('+ New rescue report', url_for('rescue_new')), args=a,
                           filt=[dict(n='q', l='Search location, animal, reporter', t='text'), dict(n='c', l='Condition', o=opts(COND)), dict(n='cs', l='Case status', o=opts(CASE)), dict(n='src', l='Source', o=[('public', 'Public report'), ('staff', 'Staff entry')]), dict(n='mine', l='Handled by', o=[('1', 'Me only')], all='Everyone')])
@app.route('/rescues/new', methods=['GET', 'POST'])
@need()
def rescue_new():
    v = {'rescue_date': today()}
    if request.method == 'POST':
        v = read(RESCUE_F); m = missing(RESCUE_F, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        else: la, ln = read_geo(); rid = ins('rescues', dict(v, reported_by=session['uid'], photo=save_photo(), lat=la, lng=ln)); flash('Rescue report saved.'); return redirect(url_for('rescue_view', rid=rid))
    return page('New rescue report', RESCUE_F, v, url_for('rescues'), geo=True)
@app.route('/rescues/<int:rid>')
@need()
def rescue_view(rid):
    r = q1('select r.*,u.full_name recorder,c.full_name claimer from rescues r left join users u on u.id=r.reported_by left join users c on c.id=r.assigned_to where r.id=%s', rid) or abort(404)
    g = re.search(r'GPS (-?\d+\.\d+), (-?\d+\.\d+)', r['location'] or '')
    return render_template('rescue_view.html', geo=True, r=r, gps=f'https://www.google.com/maps?q={g.group(1)},{g.group(2)}' if g else None, case=opts(CASE))
@app.route('/rescues/<int:rid>/case', methods=['POST'])
@need(*CARE)
def rescue_case(rid):
    s = request.form.get('case_status'); r = q1('select * from rescues where id=%s', rid)
    if s in CASE and r:
        x('update rescues set case_status=%s where id=%s', s, rid); flash('Case status updated.')
        if s != r['case_status']: tell_reporter(r, s)
    return redirect(request.form.get('next') if (request.form.get('next') or '').startswith('/') else url_for('rescue_view', rid=rid))
CASE_TEXT = {'responding': 'A rescuer is now responding to your report.', 'rescued': 'The animal has been rescued and is safe with our team. Thank you for caring!', 'closed': 'Your report has been closed. Thank you for helping this animal.', 'new': 'Your report is back in our queue.'}
def tell_reporter(r, s):
    to = tomail(r.get('reporter_email'), r.get('reporter_contact'))
    if to: notify(to, fref('R', r['id']), 'Update on your rescue report', [f"Hello {r.get('reporter_name') or ''},".replace('Hello ,', 'Hello,'), f"Report at: {r['location']}", CASE_TEXT.get(s, '')])
@app.route('/rescues/<int:rid>/claim', methods=['POST'])
@need(*CARE)
def rescue_claim(rid):
    r = q1('select * from rescues where id=%s', rid) or abort(404); new = 'responding' if r['case_status'] == 'new' else r['case_status']
    x('update rescues set assigned_to=%s, case_status=%s where id=%s', session['uid'], new, rid); flash('You took this case.')
    if new != r['case_status']: tell_reporter(r, new)
    return redirect(request.form.get('next') if (request.form.get('next') or '').startswith('/') else url_for('rescue_view', rid=rid))
@app.route('/rescues/<int:rid>/edit', methods=['GET', 'POST'])
@need(*CARE)
def rescue_edit(rid):
    r = q1('select * from rescues where id=%s', rid) or abort(404); v = r
    if request.method == 'POST':
        v = read(RESCUE_F); m = missing(RESCUE_F, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        else:
            p = save_photo()
            if p: v['photo'] = p; drop_photo(r['photo'])
            v['lat'], v['lng'] = read_geo(); upd('rescues', rid, v); flash('Rescue report updated.'); return redirect(url_for('rescue_view', rid=rid))
    return page(f'Edit rescue R-{rid:04d}', RESCUE_F, v, url_for('rescue_view', rid=rid), geo=True)
@app.route('/rescues/<int:rid>/profile', methods=['POST'])
@need(*CARE)
def rescue_profile(rid):
    r = q1('select * from rescues where id=%s', rid) or abort(404)
    if r['animal_id']: return redirect(url_for('animal_view', aid=r['animal_id']))
    aid = ins('animals', dict(name='Unnamed ' + r['species'], species=r['species'], intake_date=r['rescue_date'], status='under_care', medical_history=f"Rescued at {r['location']} ({r['animal_condition']}). {r['details'] or ''}".strip(), notes=r['description'], rescue_id=rid, photo=r['photo']))
    x("update rescues set animal_id=%s, case_status='rescued' where id=%s", aid, rid); flash('Animal profile created. Please complete the details.'); return redirect(url_for('animal_edit', aid=aid))

# ---- animals & medical ----
@app.route('/animals')
@need()
def animals():
    a = request.args; sql = 'select * from animals where 1=1'; p = []
    if a.get('q'): sql += ' and (name like %s or breed like %s or color like %s or notes like %s or medical_history like %s)'; p += [f"%{a['q'][:60]}%"] * 5
    if a.get('species'): sql += ' and species like %s'; p.append(f"%{a['species'][:40]}%")
    if a.get('status'): sql += ' and status=%s'; p.append(a['status'])
    if a.get('sex') in SEX: sql += ' and sex=%s'; p.append(a['sex'])
    sql += {'name': ' order by name', 'oldest': ' order by intake_date', 'newest': ' order by intake_date desc'}.get(a.get('sort'), ' order by id desc')
    return render_template('animals.html', items=q(sql + ' limit 300', *p), args=a, opts=opts(STATUS), sexes=opts(SEX))
@app.route('/animals/new', methods=['GET', 'POST'])
@need(*CARE)
def animal_new():
    v = {'intake_date': today(), 'status': 'under_care'}
    if request.method == 'POST':
        v = read(ANIMAL_F); m = missing(ANIMAL_F, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        else: v['photo'] = save_photo(); return redirect(url_for('animal_view', aid=ins('animals', v)))
    return page('New animal profile', ANIMAL_F, v, url_for('animals'))
@app.route('/animals/<int:aid>/edit', methods=['GET', 'POST'])
@need(*CARE)
def animal_edit(aid):
    a = q1('select * from animals where id=%s', aid) or abort(404); v = a
    if request.method == 'POST':
        v = read(ANIMAL_F); m = missing(ANIMAL_F, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        else: p = save_photo(); (v.update(photo=p), drop_photo(a['photo'])) if p else None; upd('animals', aid, v); flash('Profile updated.'); return redirect(url_for('animal_view', aid=aid))
    return page('Edit ' + a['name'], ANIMAL_F, v, url_for('animal_view', aid=aid))
@app.route('/animals/<int:aid>')
@need()
def animal_view(aid):
    a = q1('select * from animals where id=%s', aid) or abort(404)
    return render_template('animal_view.html', a=a, meds=q('select * from medical_records where animal_id=%s order by record_date desc, id desc', aid), mfs=MED_F, mvals={'record_date': today(), 'vet_name': session['name']},
                           apps=q('select p.status,d.full_name from applications p join adopters d on d.id=p.adopter_id where p.animal_id=%s', aid) if session['role'] in STAFF else [])
@app.route('/animals/<int:aid>/medical', methods=['POST'])
@need(*CARE)
def medical_add(aid):
    q1('select id from animals where id=%s', aid) or abort(404); v = read(MED_F); m = missing(MED_F, v)
    if m: flash('Please fill in: ' + ', '.join(m), 'err')
    else: ins('medical_records', dict(v, animal_id=aid, created_by=session['uid'])); flash('Medical record added.')
    return redirect(url_for('animal_view', aid=aid))
@app.route('/animals/<int:aid>/status', methods=['POST'])
@need(*CARE)
def animal_status(aid):
    st = request.form.get('status')
    if st in STATUS: x('update animals set status=%s where id=%s', st, aid); flash('Status updated.')
    return redirect(url_for('animal_view', aid=aid))
@app.route('/animals/<int:aid>/delete', methods=['POST'])
@need('admin')
def animal_delete(aid):
    a = q1('select * from animals where id=%s', aid) or abort(404); x('update rescues set animal_id=null where animal_id=%s', aid); x('delete from animals where id=%s', aid); drop_photo(a['photo']); flash('Animal deleted.'); return redirect(url_for('animals'))
@app.route('/medical/<int:mid>/done', methods=['POST'])
@need(*CARE)
def followup_done(mid):
    m = q1('select animal_id from medical_records where id=%s', mid) or abort(404)
    x('update medical_records set followup_done=1 where id=%s', mid); flash('Follow-up marked as done.')
    return redirect(request.referrer or url_for('animal_view', aid=m['animal_id']))
@app.route('/followups')
@need(*CARE)
def followups():
    rows = [R([r['followup_date'], r['name'], r['record_type'], r['details'][:70]], url_for('animal_view', aid=r['animal_id']), [('Mark done', url_for('followup_done', mid=r['id']))]) for r in
            q('select m.*,a.name from medical_records m join animals a on a.id=m.animal_id where m.followup_date is not null and m.followup_done=0 order by m.followup_date')]
    return render_template('table.html', title='Pending follow-up appointments', cols=['Date', 'Animal', 'Type', 'Details'], rows=rows, args={}, note='Sorted by date; past dates are overdue.')

# ---- adoption ----
@app.route('/adopters')
@need(*STAFF)
def adopters():
    rows = [R([r['full_name'], r['phone'], r['email'], r['address'], r['apps']], url_for('adopter_view', aid=r['id'])) for r in q('select d.*,(select count(*) from applications where adopter_id=d.id) apps from adopters d order by d.id desc')]
    return render_template('table.html', title='Adopter profiles', cols=['Name', 'Phone', 'Email', 'Address', 'Applications'], rows=rows, args={}, add=('+ New adopter', url_for('adopter_new')))
@app.route('/adopters/<int:aid>')
@need(*STAFF)
def adopter_view(aid):
    d = q1('select * from adopters where id=%s', aid) or abort(404)
    return render_template('adopter_view.html', d=d, apps=q('select p.*,a.name,a.photo,a.species from applications p join animals a on a.id=p.animal_id where p.adopter_id=%s order by p.id desc', aid))
@app.route('/adopters/new', methods=['GET', 'POST'])
@need(*STAFF)
def adopter_new():
    v = {}
    if request.method == 'POST':
        v = read(ADOPTER_F); m = missing(ADOPTER_F, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        else:
            ins('adopters', v); flash('Adopter saved.'); nxt = request.args.get('animal_id')
            return redirect(url_for('application_new', animal_id=nxt) if nxt else url_for('adopters'))
    return page('New adopter profile', ADOPTER_F, v, url_for('adopters'))
@app.route('/applications')
@need(*STAFF)
def applications():
    a = request.args; sql = 'select p.*,an.name aname,d.full_name dname from applications p join animals an on an.id=p.animal_id join adopters d on d.id=p.adopter_id'; p = []
    if a.get('status'): sql += ' where p.status=%s'; p.append(a['status'])
    act = {'pending': [('Approve', 'approve'), ('Reject', 'reject'), ('Cancel', 'cancel')], 'approved': [('Complete adoption', 'complete'), ('Cancel', 'cancel')]}
    rows = [R([f"AP-{r['id']:04d}", r['aname'], r['dname'], r['status'], str(r['applied_at'])[:10], r['completed_at'], r['notes']], None, [(l, url_for('application_act', pid=r['id'], act=k)) for l, k in act.get(r['status'], [])]) for r in q(sql + ' order by p.id desc', *p)]
    return render_template('table.html', title='Adoption applications', cols=['No.', 'Animal', 'Adopter', 'Status', 'Applied', 'Completed', 'Notes'], rows=rows, args=a, add=('+ New application', url_for('application_new')), filt=[dict(n='status', l='Status', o=opts(APPST))])
@app.route('/applications/new', methods=['GET', 'POST'])
@need(*STAFF)
def application_new():
    aid = request.args.get('animal_id', '')
    fs = [F('animal_id', 'Animal (available only)', 'select', [(str(r['id']), f"{r['name']} ({r['species']})") for r in q("select id,name,species from animals where status='available' order by name")], True),
          F('adopter_id', 'Adopter', 'select', [(str(r['id']), f"{r['full_name']} — {r['phone']}") for r in q('select id,full_name,phone from adopters order by full_name')], True), F('notes', 'Application notes', 'textarea')]
    v = {'animal_id': aid}
    if request.method == 'POST':
        v = read(fs); m = missing(fs, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        else: ins('applications', v); flash('Application submitted (pending review).'); return redirect(url_for('applications'))
    return page('New adoption application', fs, v, url_for('applications'), note='Adopter not listed? Create the adopter profile first: Adopters → + New adopter.')
@app.route('/applications/<int:pid>/<act>', methods=['POST'])
@need(*STAFF)
def application_act(pid, act):
    p = q1('select * from applications where id=%s', pid) or abort(404)
    rules = {'approve': ('pending', 'approved'), 'reject': ('pending', 'rejected'), 'cancel': (('pending', 'approved'), 'cancelled'), 'complete': ('approved', 'completed')}
    if act not in rules: abort(404)
    frm, to = rules[act]
    if p['status'] not in (frm if isinstance(frm, tuple) else (frm,)): flash('That action is not allowed for the current status.', 'err'); return redirect(url_for('applications'))
    if act == 'complete':
        an = q1('select status from animals where id=%s', p['animal_id'])
        if an['status'] != 'available': flash('Animal is not available for adoption.', 'err'); return redirect(url_for('applications'))
        x("update applications set status='completed',completed_at=%s,reviewed_by=%s where id=%s", today(), session['uid'], pid)
        x("update animals set status='adopted' where id=%s", p['animal_id'])
        x("update applications set status='rejected' where animal_id=%s and id<>%s and status in ('pending','approved')", p['animal_id'], pid)
    else: x('update applications set status=%s,reviewed_by=%s where id=%s', to, session['uid'], pid)
    flash(f'Application {to}.')
    d = q1('select d.full_name,d.email,a.name from adopters d join animals a on a.id=%s where d.id=%s', p['animal_id'], p['adopter_id']); hi = f"Hello {d['full_name']},"
    txt = {'approve': ('Your adoption application was approved', [hi, f"Good news! Your application to adopt {d['name']} has been approved.", 'Our staff will contact you to set up a meet-and-greet and the handover. Please keep your phone nearby.']),
           'reject': ('Update on your adoption application', [hi, f"Thank you for applying to adopt {d['name']}. After review we are unable to approve this application.", 'Please do not be discouraged - many other pets are waiting for a home.']),
           'cancel': ('Your adoption application was cancelled', [hi, f"Your application for {d['name']} was cancelled. If this is a mistake, please contact us."]),
           'complete': ('Adoption completed - congratulations!', [hi, f"{d['name']} is officially yours. Thank you for giving a rescued pet a loving home!"])}[act]
    notify(tomail(d['email']), fref('AP', pid), *txt); return redirect(url_for('applications'))

# ---- reports ----
RT = {'rescues': ("select r.id,r.rescue_date d,r.location,r.species,r.animal_condition cond,r.case_status cs,r.source src,r.lat,r.lng,coalesce(an.status,'no profile') status from rescues r left join animals an on an.id=r.animal_id", 'r.rescue_date', 'r.location', 'r.species', "coalesce(an.status,'no profile')", ['id', 'd', 'location', 'species', 'cond', 'cs', 'src', 'lat', 'lng', 'status']),
      'animals': ('select an.id,an.intake_date d,r.location,an.species,an.name,an.status from animals an left join rescues r on r.id=an.rescue_id', 'an.intake_date', 'r.location', 'an.species', 'an.status', ['id', 'd', 'location', 'species', 'name', 'status']),
      'volunteers': ("select v.id,date(v.created_at) d,v.address location,v.kind species,v.full_name name,v.status,v.email,v.phone from volunteer_applications v", 'date(v.created_at)', 'v.address', 'v.kind', 'v.status', ['id', 'd', 'location', 'species', 'name', 'status', 'email', 'phone']),
      'pledges': ("select p.id,date(p.created_at) d,s.name item,s.img_key species,p.pledger_name name,p.qty,p.status,p.dropoff_date from pledges p join supplies s on s.id=p.supply_id", 'date(p.created_at)', None, 's.img_key', 'p.status', ['id', 'd', 'item', 'name', 'qty', 'status', 'dropoff_date']),
      'medical': ("select m.id,m.record_date d,r.location,an.species,an.name,m.record_type status,m.medication,m.vet_name vet,m.followup_date from medical_records m join animals an on an.id=m.animal_id left join rescues r on r.id=an.rescue_id", 'm.record_date', 'r.location', 'an.species', 'm.record_type', ['id', 'd', 'location', 'species', 'name', 'status', 'medication', 'vet', 'followup_date']),
      'adoptions': ('select ap.id,date(ap.applied_at) d,r.location,an.species,an.name,ap.status,ad.full_name adopter from applications ap join animals an on an.id=ap.animal_id join adopters ad on ad.id=ap.adopter_id left join rescues r on r.id=an.rescue_id', 'date(ap.applied_at)', 'r.location', 'an.species', 'ap.status', ['id', 'd', 'location', 'species', 'name', 'status', 'adopter'])}
HEAD = dict(id='ID', d='Date', location='Location', species='Animal type', cond='Condition', status='Status', name='Name', adopter='Adopter', cs='Case status', src='Source', lat='Latitude', lng='Longitude', email='Email', phone='Phone', item='Item', qty='Qty', dropoff_date='Drop-off date', medication='Medication', vet='Vet', followup_date='Follow-up')
def run_report():
    a = request.args; t = a.get('type') if a.get('type') in RT else 'rescues'; base, dcol, lcol, scol, stcol, cols = RT[t]; w = []; p = []
    if a.get('date_from'): w.append(dcol + '>=%s'); p.append(a['date_from'])
    if a.get('date_to'): w.append(dcol + '<=%s'); p.append(a['date_to'])
    if a.get('location') and lcol: w.append(lcol + ' like %s'); p.append(f"%{a['location']}%")
    if a.get('species'): w.append(scol + ' like %s'); p.append(f"%{a['species']}%")
    if a.get('status'): w.append(stcol + '=%s'); p.append(a['status'])
    return t, cols, q(base + (' where ' + ' and '.join(w) if w else '') + f' order by {dcol} desc', *p)
@app.route('/reports')
@need(*CARE)
def report():
    t, cols, data = run_report(); a = request.args
    filt = [dict(n='type', l='Report type', o=[('rescues', 'Rescue incidents'), ('animals', 'Animals'), ('adoptions', 'Adoption applications'), ('medical', 'Medical records'), ('volunteers', 'Volunteer / foster applications'), ('pledges', 'Supply pledges')], all='Rescue incidents'), dict(n='date_from', l='From date', t='date'), dict(n='date_to', l='To date', t='date'),
            dict(n='location', l='Location contains', t='text'), dict(n='species', l='Animal type / category', t='text'), dict(n='status', l='Status / record type', o=opts(STATUS + ['pending', 'approved', 'rejected', 'completed', 'cancelled', 'declined', 'confirmed', 'received', 'no profile'] + MEDT))]
    summ = {}
    for r in data: summ[r['status']] = summ.get(r['status'], 0) + 1
    rows = [R([r[c] for c in cols]) for r in data]
    return render_template('table.html', title=f'Report: {t} ({len(data)} records)', cols=[HEAD[c] for c in cols], rows=rows, args=a, filt=filt, printable=True,
                           add=('Export CSV', url_for('report_csv', **a)), note='Filters that do not apply to a report type are ignored. By status: ' + (', '.join(f'{k.replace("_", " ")} {v}' for k, v in summ.items()) or 'no data'))
@app.route('/reports.csv')
@need(*CARE)
def report_csv():
    t, cols, data = run_report(); o = io.StringIO(); w = csv.writer(o); w.writerow([HEAD[c] for c in cols])
    for r in data: w.writerow([("'" + v if isinstance(v, str) and v[:1] in '=+-@\t\r' else v) for v in (r[c] for c in cols)])
    return Response(o.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename={t}_report.csv'})

# ---- accounts ----
@app.route('/users')
@need('admin')
def users():
    rows = [R([r['username'], r['full_name'], r['role'], 'Active' if r['active'] else 'Disabled', str(r['created_at'])[:10]], url_for('user_edit', uid=r['id'])) for r in q('select * from users order by role, full_name')]
    return render_template('table.html', title='User accounts & access', cols=['Username', 'Name', 'Role', 'Status', 'Created'], rows=rows, args={}, add=('+ New account', url_for('user_new')))
UF = [F('full_name', 'Full name', r=True), F('role', 'Role (access permissions)', 'select', opts(ROLES), True), F('active', 'Account status', 'select', [('1', 'Active'), ('0', 'Disabled')], True), F('password', 'Password (8+ characters; leave blank to keep current)', 'password')]
@app.route('/users/new', methods=['GET', 'POST'])
@need('admin')
def user_new():
    fs = [F('username', 'Username', r=True)] + UF; v = {'active': '1'}
    if request.method == 'POST':
        v = read(fs); m = missing(fs, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif not v['password'] or len(v['password']) < 8: flash('Password must be at least 8 characters.', 'err')
        elif q1('select 1 from users where username=%s', v['username']): flash('Username already exists.', 'err')
        else:
            pw = v.pop('password'); ins('users', dict(v, pw_hash=gph(pw), active=int(v['active']))); flash('Account created.'); return redirect(url_for('users'))
    return page('New account', fs, v, url_for('users'))
@app.route('/users/<int:uid>/edit', methods=['GET', 'POST'])
@need('admin')
def user_edit(uid):
    u = q1('select * from users where id=%s', uid) or abort(404); v = dict(u, password=None)
    if request.method == 'POST':
        v = read(UF); m = missing(UF, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif uid == session['uid'] and (v['role'] != 'admin' or v['active'] != '1'): flash('You cannot demote or disable your own account.', 'err')
        elif v['password'] and len(v['password']) < 8: flash('Password must be at least 8 characters.', 'err')
        else:
            pw = v.pop('password'); v['active'] = int(v['active'])
            if pw: v['pw_hash'] = gph(pw)
            upd('users', uid, v); flash('Account updated.'); return redirect(url_for('users'))
    return page('Edit account: ' + u['username'], UF, v, url_for('users'))


# ======================= v3: track, volunteers, wishlist, queue, map, search, about =======================
def done(h, ref, msg, again, againl):
    session['thanks'] = dict(h=h, ref=ref, msg=msg, again=again, againl=againl); return redirect(url_for('thanks'))
@app.route('/thanks')
def thanks():
    t = session.pop('thanks', None)
    if not t: return redirect(url_for('home'))
    return render_template('thanks.html', title='Thank you', **t)
@app.route('/about')
def about(): return render_template('about.html', title='About the system')

# ---- track a request (public) ----
def digits(s): return re.sub(r'\D', '', s or '')
def same_contact(given, *known):
    g = (given or '').strip().lower(); gd = digits(g)
    for k in known:
        k = (k or '').strip().lower()
        if not k: continue
        if '@' in g and '@' in k and g == k: return True
        if '@' not in g and len(gd) >= 7 and len(digits(k)) >= 7 and digits(k)[-7:] == gd[-7:]: return True
    return False
def flow(steps, cur, bad=False, bad_label=None):
    steps = list(steps)
    if bad and bad_label: steps[cur] = bad_label
    return dict(steps=steps, cur=cur, bad=bad)
def track_lookup(ref, contact):
    m = re.fullmatch(r'(RH|AP|VF|PL|R)-?0*(\d+)', ref.strip().upper().replace(' ', ''))
    if not m or len(m.group(2)) > 9: return None
    k, i = m.group(1), int(m.group(2)); d = None
    if k == 'R':
        r = q1('select * from rescues where id=%s', i)
        if r and same_contact(contact, r['reporter_contact'], r['reporter_email']):
            an = q1('select name,status from animals where id=%s', r['animal_id']) if r['animal_id'] else None
            lines = [('Reported on', r['rescue_date']), ('Place', r['location']), ('Animal', r['species'])] + ([('Animal profile', f"{an['name']} - {an['status'].replace('_', ' ')}")] if an else [])
            d = dict(title='Rescue report', status=r['case_status'], text={'new': 'Received - waiting for a rescuer', 'responding': 'A rescuer is responding', 'rescued': 'Animal rescued', 'closed': 'Case closed'}[r['case_status']],
                     lines=lines, **flow(['Report received', 'Rescuer responding', 'Animal rescued', 'Case closed'], CASE.index(r['case_status'])))
    elif k == 'RH':
        r = q1('select * from rehome_requests where id=%s', i)
        if r and same_contact(contact, r['contact'], r['email']):
            c = dict(pending=1, accepted=2, declined=2)[r['status']]
            d = dict(title='Rehome request', status=r['status'], text={'pending': 'Under review', 'accepted': 'Accepted - staff will arrange the handover', 'declined': 'Declined'}[r['status']],
                     lines=[('Pet', r['pet_name']), ('Sent on', str(r['created_at'])[:10])], **flow(['Request received', 'Under review', 'Accepted'], c, r['status'] == 'declined', 'Declined'))
    elif k == 'AP':
        r = q1('select p.*,a.name pet,d.phone,d.email from applications p join animals a on a.id=p.animal_id join adopters d on d.id=p.adopter_id where p.id=%s', i)
        if r and same_contact(contact, r['phone'], r['email']):
            c = dict(pending=1, approved=2, completed=3, rejected=2, cancelled=2)[r['status']]
            d = dict(title='Adoption application', status=r['status'], text={'pending': 'Under review', 'approved': 'Approved - staff will contact you for the handover', 'completed': 'Adoption completed', 'rejected': 'Not approved', 'cancelled': 'Cancelled'}[r['status']],
                     lines=[('Pet', r['pet']), ('Applied on', str(r['applied_at'])[:10])], **flow(['Application received', 'Under review', 'Approved', 'Adoption completed'], c, r['status'] in ('rejected', 'cancelled'), r['status'].title() if r['status'] == 'cancelled' else 'Not approved'))
    elif k == 'VF':
        r = q1('select * from volunteer_applications where id=%s', i)
        if r and same_contact(contact, r['phone'], r['email']):
            c = dict(pending=1, approved=2, declined=2)[r['status']]
            d = dict(title=f"{r['kind'].title()} application", status=r['status'], text={'pending': 'Under review', 'approved': 'Approved - welcome to the team!', 'declined': 'Not accepted this time'}[r['status']],
                     lines=[('Applicant', r['full_name']), ('Sent on', str(r['created_at'])[:10])], **flow(['Application received', 'Under review', 'Approved'], c, r['status'] == 'declined', 'Not accepted'))
    elif k == 'PL':
        r = q1('select p.*,s.name item,s.unit from pledges p join supplies s on s.id=p.supply_id where p.id=%s', i)
        if r and same_contact(contact, r['phone'], r['email']):
            c = dict(pending=0, confirmed=1, received=2, declined=1)[r['status']]
            d = dict(title='Supply pledge', status=r['status'], text={'pending': 'Waiting for staff to confirm', 'confirmed': 'Confirmed - please bring the items', 'received': 'Items received - thank you!', 'declined': 'Not needed right now'}[r['status']],
                     lines=[('Item', f"{r['qty']} {r['unit']} - {r['item']}"), ('Planned drop-off', r['dropoff_date'] or 'any day')], **flow(['Pledge sent', 'Confirmed by staff', 'Items received'], c, r['status'] == 'declined', 'Not needed'))
    if d: d['ref'] = fref(k, i)
    return d
@app.route('/track', methods=['GET', 'POST'])
def track():
    ref = (request.values.get('ref') or '').strip()[:20]; contact = (request.form.get('contact') or '').strip()[:120] if request.method == 'POST' else ''; res = None; tried = False
    if request.method == 'POST' and ref and contact:
        tried = True
        if too_many('track', 25, 600): flash('Too many lookups from this device. Please try again in a few minutes.', 'err'); tried = False
        else: res = track_lookup(ref, contact)
    return render_template('track.html', title='Track my request', ref=ref, contact=contact, res=res, tried=tried)

# ---- public pets list with search ----
@app.route('/pets')
def pets_public():
    a = request.args; sql = "select * from animals where status='available'"; p = []
    if a.get('q'): sql += ' and (name like %s or breed like %s or color like %s or medical_history like %s)'; p += [f"%{a['q'][:60]}%"] * 4
    if a.get('species'): sql += ' and species=%s'; p.append(a['species'][:40])
    if a.get('sex') in ('male', 'female'): sql += ' and sex=%s'; p.append(a['sex'])
    age = a.get('age')
    if age == 'young': sql += ' and age_years<=1'
    elif age == 'adult': sql += ' and age_years>1 and age_years<=6'
    elif age == 'senior': sql += ' and age_years>6'
    kinds = [r['species'] for r in q("select distinct species from animals where status='available' order by species")]
    return render_template('pets_public.html', title='Adoptable pets', items=q(sql + ' order by id desc limit 120', *p), args=a, kinds=kinds)

# ---- public volunteer / foster application ----
VOL_F = [F('kind', 'I want to', 'select', [('volunteer', 'Volunteer (walking, cleaning, events, transport)'), ('foster', 'Foster animals at my home'), ('both', 'Both')], True), F('full_name', 'Full name', r=True), F('email', 'Email (we send our decision here)', 'email', r=True), F('phone', 'Phone number', 'tel', r=True),
         F('address', 'Address / barangay'), F('availability', 'When are you available? (days and hours)', 'textarea'), F('experience', 'Experience with animals', 'textarea'),
         F('home_notes', 'For fostering: your home, space, other pets, who lives with you', 'textarea'), FD('animals_ok', 'Animals you are comfortable with', ['Dogs', 'Cats', 'Dogs and cats', 'Puppies / kittens', 'Rabbits', 'Birds', 'Any'])]
@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer():
    v = {}; rows = areas(); fs = with_area(VOL_F, 'address', rows)
    if request.method == 'POST':
        if request.form.get('website'): abort(400)
        v = read(fs); m = missing(fs, v)
        if not rows: flash(CLOSED_MSG, 'err')
        elif m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif not EMAIL_RE.match(v['email']): flash('Please enter a valid email address.', 'err')
        elif (e := area_error(v['area_id'], rows=rows)): flash(e, 'err')
        elif too_many('volunteer'): flash('Too many requests from this device. Please contact the center directly.', 'err')
        else: v['address'] = place_text(v['address'], v['area_id'], rows); v['area_id'] = int(v['area_id']); vid = ins('volunteer_applications', v); alert_staff(f"New volunteer/foster application {fref('VF', vid)}", [f"{v.get('full_name', '')} applied to {v.get('kind', 'help')}."], url_for('volunteers')); return done('Application received', fref('VF', vid), 'Our team will review your application and email you our decision. Thank you for offering to help the animals!', url_for('home'), 'Back to home')
    return render_template('volunteer.html', title='Volunteer & foster', fs=fs, vals=v, svc=area_names(rows), closed=not rows)
@app.route('/volunteers')
@need(*STAFF)
def volunteers():
    a = request.args; sql = 'select * from volunteer_applications where 1=1'; p = []
    if a.get('status') in ('pending', 'approved', 'declined'): sql += ' and status=%s'; p.append(a['status'])
    if a.get('kind') in ('volunteer', 'foster', 'both'): sql += ' and kind=%s'; p.append(a['kind'])
    if a.get('q'): sql += ' and (full_name like %s or email like %s or phone like %s)'; p += [f"%{a['q'][:60]}%"] * 3
    return render_template('volunteers.html', title='Volunteer & foster applications', items=q(sql + " order by status='pending' desc, id desc limit 200", *p), args=a)
@app.route('/volunteers/<int:vid>/<act>', methods=['POST'])
@need(*STAFF)
def volunteer_act(vid, act):
    r = q1('select * from volunteer_applications where id=%s', vid) or abort(404)
    if act not in ('approve', 'decline') or r['status'] != 'pending': flash('That application was already handled.', 'err'); return redirect(url_for('volunteers'))
    note = (request.form.get('note') or '').strip()[:500] or None; st = 'approved' if act == 'approve' else 'declined'
    x('update volunteer_applications set status=%s,staff_note=%s,reviewed_by=%s where id=%s', st, note, session['uid'], vid); flash(f'Application {st}.')
    hi = f"Hello {r['full_name']},"; extra = [f'Note from our team: {note}'] if note else []
    if act == 'approve': notify(r['email'], fref('VF', vid), 'Your volunteer / foster application was approved', [hi, f"Welcome! We approved your application to {'foster' if r['kind'] == 'foster' else 'volunteer' if r['kind'] == 'volunteer' else 'volunteer and foster'}.", 'Our coordinator will contact you with the orientation schedule.'] + extra)
    else: notify(r['email'], fref('VF', vid), 'Update on your volunteer / foster application', [hi, 'Thank you for offering to help. We are unable to accept your application at this time, but you are welcome to apply again later.'] + extra)
    return redirect(url_for('volunteers'))

# ---- supply wishlist & pledges (items only - no online payment) ----
NEED_KEYS = [(i['key'], i['title']) for i in NEEDS]
def supply_rows(only_active=True):
    rows = q("select s.*,coalesce((select sum(p.qty) from pledges p where p.supply_id=s.id and p.status='received'),0) got,coalesce((select sum(p.qty) from pledges p where p.supply_id=s.id and p.status='confirmed'),0) promised from supplies s" + (' where s.active=1' if only_active else '') + " order by s.priority='urgent' desc, s.priority='high' desc, s.id desc")
    for r in rows:
        r['got'] = int(r['got']); r['promised'] = int(r['promised']); r['pct_got'] = min(100, round(100 * r['got'] / max(1, r['qty_needed']))); r['pct_prom'] = min(100 - r['pct_got'], round(100 * r['promised'] / max(1, r['qty_needed'])))
    return rows
PLEDGE_F = [F('pledger_name', 'Your name', r=True), F('phone', 'Phone number', 'tel', r=True), F('email', 'Email (we confirm here)', 'email'), F('qty', 'How many are you pledging?', 'number', r=True), F('dropoff_date', 'When can you drop it off?', 'date'), F('note', 'Note (optional)')]
@app.route('/wishlist')
def wishlist(): return render_template('wishlist.html', title='Supply wishlist', items=supply_rows())
@app.route('/wishlist/<int:sid>/pledge', methods=['GET', 'POST'])
def pledge(sid):
    s = q1('select * from supplies where id=%s and active=1', sid) or abort(404); v = {'qty': 1}
    if request.method == 'POST':
        if request.form.get('website'): abort(400)
        v = read(PLEDGE_F); m = missing(PLEDGE_F, v)
        try: qty = int(float(v['qty'] or 0))
        except (TypeError, ValueError): qty = 0
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif not 1 <= qty <= 10000: flash('Quantity must be between 1 and 10,000.', 'err')
        elif v['email'] and not EMAIL_RE.match(v['email']): flash('Please enter a valid email address.', 'err')
        elif too_many('pledge'): flash('Too many pledges from this device. Please contact the center directly.', 'err')
        else:
            v['qty'] = qty; pid = ins('pledges', dict(v, supply_id=sid)); alert_staff(f"New supply pledge {fref('PL', pid)}", [f"{v.get('pledger_name', '')} pledged {qty} of a wishlist item."], url_for('pledges'))
            return done('Pledge received - thank you!', fref('PL', pid), f"Please bring {qty} {s['unit']} of {s['name']} to the rescue center. Our staff will confirm your pledge" + (' by email.' if v['email'] else ' - keep your phone nearby.'), url_for('wishlist'), 'Back to the wishlist')
    return render_template('pledge.html', title='Pledge: ' + s['name'], s=s, fs=PLEDGE_F, vals=v)
@app.route('/supplies')
@need(*STAFF)
def supplies(): return render_template('supplies.html', title='Supply wishlist (manage)', items=supply_rows(False))
SUP_F = [F('name', 'Item', r=True), F('img_key', 'Picture', 'select', NEED_KEYS, True), F('unit', 'Unit (pcs, kg, sacks...)', r=True), F('qty_needed', 'Quantity needed', 'number', r=True), F('priority', 'Priority', 'select', [('urgent', 'Urgent'), ('high', 'High'), ('normal', 'Normal')], True), F('notes', 'Notes shown to donors (brand, size...)')]
def sup_clean(v):
    try: v['qty_needed'] = max(1, min(100000, int(float(v['qty_needed']))))
    except (TypeError, ValueError): v['qty_needed'] = 1
    return v
@app.route('/supplies/new', methods=['GET', 'POST'])
@need(*STAFF)
def supply_new():
    v = {'priority': 'normal', 'unit': 'pcs'}
    if request.method == 'POST':
        v = read(SUP_F); m = missing(SUP_F, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        else: ins('supplies', sup_clean(v)); flash('Item added to the wishlist.'); return redirect(url_for('supplies'))
    return page('New wishlist item', SUP_F, v, url_for('supplies'))
@app.route('/supplies/<int:sid>/edit', methods=['GET', 'POST'])
@need(*STAFF)
def supply_edit(sid):
    s = q1('select * from supplies where id=%s', sid) or abort(404); v = s
    if request.method == 'POST':
        v = read(SUP_F); m = missing(SUP_F, v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        else: upd('supplies', sid, sup_clean(v)); flash('Item updated.'); return redirect(url_for('supplies'))
    return page('Edit: ' + s['name'], SUP_F, v, url_for('supplies'))
@app.route('/supplies/<int:sid>/toggle', methods=['POST'])
@need(*STAFF)
def supply_toggle(sid):
    s = q1('select * from supplies where id=%s', sid) or abort(404); x('update supplies set active=%s where id=%s', 0 if s['active'] else 1, sid); flash('Item hidden from the public wishlist.' if s['active'] else 'Item is now visible on the public wishlist.'); return redirect(url_for('supplies'))
@app.route('/pledges')
@need(*STAFF)
def pledges():
    a = request.args; sql = 'select p.*,s.name item,s.unit from pledges p join supplies s on s.id=p.supply_id'; w = []; prm = []
    if a.get('status'): sql += ' where p.status=%s'; prm.append(a['status'])
    act = {'pending': [('Confirm', 'confirm'), ('Decline', 'decline')], 'confirmed': [('Mark received', 'receive'), ('Decline', 'decline')]}
    rows = [R([fref('PL', r['id']), r['item'], f"{r['qty']} {r['unit']}", r['pledger_name'], r['phone'] + (' / ' + r['email'] if r['email'] else ''), r['dropoff_date'], r['status']], None, [(l, url_for('pledge_act', pid=r['id'], act=k)) for l, k in act.get(r['status'], [])]) for r in q(sql + ' order by p.status=\'pending\' desc, p.id desc limit 300', *prm)]
    return render_template('table.html', title='Supply pledges', cols=['No.', 'Item', 'Quantity', 'Donor', 'Contact', 'Drop-off', 'Status'], rows=rows, args=a, filt=[dict(n='status', l='Status', o=opts(['pending', 'confirmed', 'received', 'declined']))], note='Pledges are items only - the system has no online payment. "Received" items count toward the wishlist progress bar.')
@app.route('/pledges/<int:pid>/<act>', methods=['POST'])
@need(*STAFF)
def pledge_act(pid, act):
    r = q1('select p.*,s.name item,s.unit from pledges p join supplies s on s.id=p.supply_id where p.id=%s', pid) or abort(404)
    rules = {'confirm': ('pending', 'confirmed'), 'receive': ('confirmed', 'received'), 'decline': (('pending', 'confirmed'), 'declined')}
    if act not in rules: abort(404)
    frm, to = rules[act]
    if r['status'] not in (frm if isinstance(frm, tuple) else (frm,)): flash('That action is not allowed for the current status.', 'err'); return redirect(url_for('pledges'))
    x('update pledges set status=%s,reviewed_by=%s where id=%s', to, session['uid'], pid); flash(f'Pledge {to}.')
    hi = f"Hello {r['pledger_name']},"; what = f"{r['qty']} {r['unit']} of {r['item']}"
    txt = {'confirm': ('Your pledge was confirmed', [hi, f'Thank you! We confirmed your pledge of {what}.', 'Please bring it to the rescue center' + (f" on {r['dropoff_date']}." if r['dropoff_date'] else ' any day during opening hours.')]),
           'receive': ('We received your donation - thank you!', [hi, f'We received {what}. The animals say thank you!']),
           'decline': ('Update on your pledge', [hi, f"Thank you for offering {what}. We do not need it right now, but we really appreciate your kindness."])}[act]
    notify(tomail(r['email']), fref('PL', pid), *txt); return redirect(url_for('pledges'))

# ---- case queues ----
@app.route('/queue')
@need(*CARE)
def queue():
    mine = request.args.get('mine') == '1'; soon = (date.today() + timedelta(days=7)).isoformat(); sql = "select r.*,u.full_name who from rescues r left join users u on u.id=r.assigned_to where r.case_status in ('new','responding')"; p = []
    if mine: sql += ' and r.assigned_to=%s'; p.append(session['uid'])
    cases = q(sql + " order by case r.animal_condition when 'critical' then 0 when 'injured' then 1 when 'sick' then 2 else 3 end, r.id", *p)
    for r in cases: r['wait'] = ago(r['created_at'])
    st = session['role'] in STAFF
    return render_template('queue.html', title='Case queues', cases=cases, mine=mine, st=st,
        apps=q("select p.id,a.name aname,d.full_name dname,p.applied_at from applications p join animals a on a.id=p.animal_id join adopters d on d.id=p.adopter_id where p.status in ('pending','approved') order by p.status='pending' desc, p.id limit 30") if st else [],
        rehome=q("select * from rehome_requests where status='pending' order by id limit 30") if st else [], vols=q("select * from volunteer_applications where status='pending' order by id limit 30") if st else [],
        pls=q("select p.*,s.name item,s.unit from pledges p join supplies s on s.id=p.supply_id where p.status in ('pending','confirmed') order by p.status='pending' desc, p.id limit 30") if st else [],
        due=q('select m.id,m.animal_id,m.followup_date,m.record_type,a.name from medical_records m join animals a on a.id=m.animal_id where m.followup_date is not null and m.followup_done=0 and m.followup_date<=%s order by m.followup_date limit 30', soon), today=today())

# ---- map of rescue cases ----
@app.route('/map')
@need()
def case_map():
    a = request.args; sql = 'select id,lat,lng,animal_condition c,case_status cs,species,location,rescue_date,source from rescues where lat is not null and lng is not null'; p = []
    if a.get('cs') in CASE: sql += ' and case_status=%s'; p.append(a['cs'])
    elif a.get('cs') == 'open': sql += " and case_status in ('new','responding')"
    if a.get('c') in COND: sql += ' and animal_condition=%s'; p.append(a['c'])
    pts = [dict(id=r['id'], ref=fref('R', r['id']), lat=float(r['lat']), lng=float(r['lng']), cond=r['c'], case=r['cs'], species=r['species'], location=r['location'], date=str(r['rescue_date']), url=url_for('rescue_view', rid=r['id'])) for r in q(sql + ' order by id desc limit 1000', *p)]
    return render_template('map.html', title='Rescue map', pts=pts, args=a, nopin=n('select count(*) n from rescues where lat is null'))

# ---- staff search ----
@app.route('/search')
@need()
def search():
    s = (request.args.get('q') or '').strip()[:60]; groups = []; st = session['role'] in STAFF
    if s:
        m = re.fullmatch(r'R-?0*(\d+)', s.upper().replace(' ', ''))
        if m and len(m.group(1)) < 9 and q1('select id from rescues where id=%s', int(m.group(1))): return redirect(url_for('rescue_view', rid=int(m.group(1))))
        k = f'%{s}%'
        def grp(title, rows, mk):
            if rows: groups.append((title, [mk(r) for r in rows]))
        grp('Animals', q('select * from animals where name like %s or breed like %s or species like %s or color like %s or notes like %s order by id desc limit 15', k, k, k, k, k), lambda r: (f"{r['name']} - {r['species']}", f"{r['status'].replace('_', ' ')} · {r['breed'] or 'no breed'}", url_for('animal_view', aid=r['id'])))
        grp('Rescue reports', q('select * from rescues where location like %s or species like %s or description like %s or reporter_name like %s or reporter_contact like %s order by id desc limit 15', k, k, k, k, k), lambda r: (f"{fref('R', r['id'])} - {r['species']} at {r['location']}", f"{r['animal_condition']} · {r['case_status']}", url_for('rescue_view', rid=r['id'])))
        if st:
            grp('Adopters', q('select * from adopters where full_name like %s or phone like %s or email like %s order by id desc limit 15', k, k, k), lambda r: (r['full_name'], f"{r['phone']} · {r['email'] or ''}", url_for('adopter_view', aid=r['id'])))
            grp('Rehome requests', q('select * from rehome_requests where pet_name like %s or owner_name like %s or contact like %s order by id desc limit 10', k, k, k), lambda r: (f"{fref('RH', r['id'])} - {r['pet_name']} ({r['owner_name']})", r['status'], url_for('requests_list')))
            grp('Volunteer / foster', q('select * from volunteer_applications where full_name like %s or email like %s or phone like %s order by id desc limit 10', k, k, k), lambda r: (f"{fref('VF', r['id'])} - {r['full_name']}", f"{r['kind']} · {r['status']}", url_for('volunteers', q=s)))
            grp('Supply pledges', q('select p.*,s.name item from pledges p join supplies s on s.id=p.supply_id where p.pledger_name like %s or p.phone like %s or s.name like %s order by p.id desc limit 10', k, k, k), lambda r: (f"{fref('PL', r['id'])} - {r['item']} x{r['qty']}", f"{r['pledger_name']} · {r['status']}", url_for('pledges')))
    return render_template('search.html', title='Search', s=s, groups=groups)

# ---- email log ----
@app.route('/emails')
@need(*STAFF)
def emails():
    rows = [R([str(r['created_at'])[:16], r['to_email'], r['subject'], r['status'].replace('_', ' '), r['ref']], url_for('email_view', eid=r['id'])) for r in q('select * from email_log order by id desc limit 200')]
    return render_template('table.html', title='Email log', cols=['When', 'To', 'Subject', 'Status', 'Ref'], rows=rows, args={}, note='Every message the system sends when staff approve or decline a request. If SMTP is not set up, the message is kept here instead of being delivered (see README, step 3).')
@app.route('/emails/<int:eid>')
@need(*STAFF)
def email_view(eid): return render_template('email_view.html', title='Email', e=q1('select * from email_log where id=%s', eid) or abort(404))


# ======================= v4.4: service areas (admin decides which places the public may use) =======================
AREA_F = [F('name', 'Name of the place (shown to the public)', r=True), F('kind', 'Type', 'select', AREA_KINDS, True), F('radius_km', 'Accepted distance from the pin (km) - only used when there is no boundary', 'number'), F('note', 'Note (optional, only staff see this)')]
AREA_PICK = dict(geo=True, area_find=True, pick_title='Pin of this place', pick_hint='Best way: search the place above (any barangay, municipality, city, region or country in the world) and pick it - its real boundary is used. For a custom spot with no boundary, drop a pin here and set the distance (circle). Faint shapes are the other places already on your list.')
def area_clean(v):
    la, ln = read_geo()
    try: r = float(v['radius_km'])
    except (TypeError, ValueError): r = None
    gj = request.form.get('geojson', '').strip()
    if la is None: return 'Search the place above, or drop a pin on the map.'
    if gj:
        g = clean_geojson(gj)
        if not g: return 'The boundary could not be read. Search the place again, or remove the boundary and use a circle.'
        v['geojson'] = g; r = 1.0
    else:
        if r is None or not 0.3 <= r <= 60: return 'Search the place above to use its real boundary, or set the accepted distance (0.3 to 60 km) for a circle.'
        v['geojson'] = None
    v['name'] = v['name'][:100]; v['lat'], v['lng'], v['radius_km'] = la, ln, r; return None
def area_rows():
    return q("select a.id,a.name,a.kind,a.lat,a.lng,a.radius_km,a.active,a.note,(a.geojson is not null) has_poly, (select count(*) from rescues where area_id=a.id) + (select count(*) from rehome_requests where area_id=a.id) + (select count(*) from volunteer_applications where area_id=a.id) + (select count(*) from adopters where area_id=a.id) used "
             "from service_areas a order by a.active desc, field(a.kind,'country','region','city','municipality','barangay','place'), a.name")
@app.route('/areas')
@need('admin')
def areas_list(): return render_template('areas.html', title='Service areas', items=area_rows(), cfg=area_cfg(False, areas(False)))
@app.route('/areas/new', methods=['GET', 'POST'])
@need('admin')
def area_new():
    v = {'kind': 'municipality', 'radius_km': 8, 'geojson': ''}
    if request.method == 'POST':
        v = read(AREA_F); m = missing(AREA_F, v); e = None if m else area_clean(v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif e: flash(e, 'err')
        else:
            try: ins('service_areas', v); flash(f"{v['name']} added. The public can now send requests from there."); return redirect(url_for('areas_list'))
            except pymysql.err.IntegrityError: flash('That place is already on the list.', 'err')
        v['lat'], v['lng'] = read_geo(); v['geojson'] = request.form.get('geojson', '')
    return page('Add a place', AREA_F, v, url_for('areas_list'), svc_cfg=area_cfg(False, areas(False)), **AREA_PICK)
@app.route('/areas/<int:aid>/edit', methods=['GET', 'POST'])
@need('admin')
def area_edit(aid):
    a = q1('select * from service_areas where id=%s', aid) or abort(404); v = a
    if request.method == 'POST':
        v = read(AREA_F); m = missing(AREA_F, v); e = None if m else area_clean(v)
        if m: flash('Please fill in: ' + ', '.join(m), 'err')
        elif e: flash(e, 'err')
        else:
            try: upd('service_areas', aid, v); flash('Place updated.'); return redirect(url_for('areas_list'))
            except pymysql.err.IntegrityError: flash('Another place already has that name.', 'err')
        v['lat'], v['lng'] = read_geo(); v['geojson'] = request.form.get('geojson', '')
    return page('Edit: ' + a['name'], AREA_F, v, url_for('areas_list'), svc_cfg=area_cfg(False, areas(False)), **AREA_PICK)
@app.route('/areas/<int:aid>/toggle', methods=['POST'])
@need('admin')
def area_toggle(aid):
    a = q1('select * from service_areas where id=%s', aid) or abort(404); x('update service_areas set active=%s where id=%s', 0 if a['active'] else 1, aid)
    flash(f"{a['name']} is now closed - the public can no longer send requests from there." if a['active'] else f"{a['name']} is open again."); return redirect(url_for('areas_list'))
@app.route('/areas/<int:aid>/delete', methods=['POST'])
@need('admin')
def area_delete(aid):
    a = next((r for r in area_rows() if r['id'] == aid), None) or abort(404)
    if a['used']: flash(f"{a['name']} already has {a['used']} record(s), so it cannot be deleted. Use Close instead.", 'err')
    else: x('delete from service_areas where id=%s', aid); flash('Place deleted.')
    return redirect(url_for('areas_list'))

@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(400)
@app.errorhandler(413)
def err(e): return render_template('error.html', e=e), e.code

if __name__ == '__main__': app.run(debug=False)
