"""Sample data for Davao del Sur: service areas (the places the public may report from), 44 animals with generated portraits, rescue reports, medical records, adopters, applications, rehome requests, volunteers, wishlist items and pledges."""
import os
from datetime import date, timedelta
HERE = os.path.dirname(os.path.abspath(__file__))
def shade(h, f):
    r, g, b = [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(max(0, min(255, int(c * f))) for c in (r, g, b))
EYES = '<circle cx="168" cy="150" r="9" fill="#2b2220"/><circle cx="232" cy="150" r="9" fill="#2b2220"/><circle cx="171" cy="147" r="3" fill="#fff"/><circle cx="235" cy="147" r="3" fill="#fff"/>'
def avatar(sp, col):
    d, l = shade(col, .72), shade(col, 1.18)
    bg = {'dog': '#fde8cf', 'cat': '#e3ecf7', 'rabbit': '#f6e3ee', 'bird': '#e0f3e4'}[sp]
    if sp == 'dog':
        b = f'<ellipse cx="118" cy="125" rx="30" ry="58" fill="{d}" transform="rotate(18 118 125)"/><ellipse cx="282" cy="125" rx="30" ry="58" fill="{d}" transform="rotate(-18 282 125)"/><circle cx="200" cy="165" r="88" fill="{col}"/><ellipse cx="200" cy="202" rx="46" ry="32" fill="{l}"/><ellipse cx="200" cy="184" rx="15" ry="10" fill="#2b2220"/><path d="M190 214q10 24 20 0z" fill="#e8798f"/><path d="M200 194v10M184 206q16 14 32 0" stroke="#2b2220" stroke-width="3" fill="none"/>' + EYES
    elif sp == 'cat':
        b = f'<polygon points="122,125 138,42 192,92" fill="{col}"/><polygon points="278,125 262,42 208,92" fill="{col}"/><polygon points="136,105 142,66 172,92" fill="#f2a7b8"/><polygon points="264,105 258,66 228,92" fill="#f2a7b8"/><circle cx="200" cy="165" r="86" fill="{col}"/><ellipse cx="200" cy="198" rx="34" ry="24" fill="{l}"/><ellipse cx="168" cy="152" rx="10" ry="13" fill="#d9e86a"/><ellipse cx="232" cy="152" rx="10" ry="13" fill="#d9e86a"/><ellipse cx="168" cy="152" rx="3.5" ry="11" fill="#2b2220"/><ellipse cx="232" cy="152" rx="3.5" ry="11" fill="#2b2220"/><polygon points="191,184 209,184 200,196" fill="#e8798f"/><path d="M200 196v8M188 208q12 8 12-4q0 12 12 4" stroke="#2b2220" stroke-width="2.5" fill="none"/><path d="M150 190l-52-8M150 200l-52 6M250 190l52-8M250 200l52 6" stroke="#2b2220" stroke-width="2" opacity=".55"/>'
    elif sp == 'rabbit':
        b = f'<ellipse cx="160" cy="78" rx="24" ry="72" fill="{col}"/><ellipse cx="240" cy="78" rx="24" ry="72" fill="{col}"/><ellipse cx="160" cy="82" rx="11" ry="52" fill="#f2a7b8"/><ellipse cx="240" cy="82" rx="11" ry="52" fill="#f2a7b8"/><circle cx="200" cy="180" r="76" fill="{col}"/><ellipse cx="200" cy="208" rx="34" ry="24" fill="{l}"/><circle cx="172" cy="165" r="8" fill="#2b2220"/><circle cx="228" cy="165" r="8" fill="#2b2220"/><ellipse cx="200" cy="192" rx="9" ry="6" fill="#e8798f"/><path d="M200 198v8M190 210q10 8 10-4q0 12 10 4" stroke="#2b2220" stroke-width="2.5" fill="none"/>'
    else:
        b = f'<circle cx="200" cy="170" r="88" fill="{col}"/><ellipse cx="200" cy="205" rx="52" ry="42" fill="{l}"/><ellipse cx="128" cy="180" rx="26" ry="46" fill="{d}" transform="rotate(20 128 180)"/><circle cx="200" cy="148" r="12" fill="#fff"/><circle cx="203" cy="148" r="6" fill="#2b2220"/><polygon points="174,170 226,170 200,206" fill="#f59f2a"/><path d="M176 60q20 40 24 62M200 52q6 40 0 68M224 60q-16 38-22 62" stroke="{d}" stroke-width="9" stroke-linecap="round" fill="none"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><rect width="400" height="300" fill="{bg}"/><ellipse cx="200" cy="278" rx="140" ry="14" fill="#000" opacity=".08"/>{b}</svg>'
C = dict(brown='#8b5a3c', grey='#8d949b', cream='#e8d3a8', white='#f4f1ea', golden='#d9a441', tan='#c79a64', orange='#e38b3a', black='#4a423d', green='#7cc36b')
import random
MARK = 'Sample record (Davao del Sur demo).'
# name, kind, centre lat, centre lng, accepted radius in km  (approximate centres - the admin can move the pin on the map)
AREAS = [('Digos City', 'city', 6.7497, 125.3572, 14), ('Bansalan', 'municipality', 6.7817, 125.2189, 12), ('Hagonoy', 'municipality', 6.6890, 125.3180, 12),
         ('Kiblawan', 'municipality', 6.6100, 125.2200, 13), ('Magsaysay', 'municipality', 6.7500, 125.1600, 13), ('Malalag', 'municipality', 6.6020, 125.3960, 12),
         ('Matanao', 'municipality', 6.7000, 125.2400, 12), ('Padada', 'municipality', 6.6400, 125.3400, 12), ('Santa Cruz', 'municipality', 6.8340, 125.4100, 14), ('Sulop', 'municipality', 6.5700, 125.3500, 12)]
PLACES = {  # streets / barangays used in the sample reports
 'Digos City': ['Rizal Avenue', 'Digos Public Market area', 'Brgy. Zone 1', 'Brgy. Aplaya', 'Brgy. Cogon', 'Brgy. Matti', 'Brgy. Kapatagan', 'Brgy. San Jose', 'Brgy. Ruparan', 'Brgy. Tres de Mayo', 'Brgy. Sinawilan', 'Brgy. Goma'],
 'Bansalan': ['Poblacion, near the public market', 'Brgy. Darapuay', 'Brgy. Eman', 'Brgy. Managa', 'Brgy. Kinuskusan', 'Brgy. Mabuhay', 'Brgy. Libertad', 'Brgy. Tubod'],
 'Hagonoy': ['Poblacion', 'Brgy. Guihing', 'Brgy. La Union', 'Brgy. Mabini', 'Brgy. Leling', 'Brgy. Lanuro', 'Brgy. Sacub', 'Brgy. San Isidro'],
 'Kiblawan': ['Poblacion', 'Brgy. Bagong Silang', 'Brgy. Molopolo', 'Brgy. Pasig', 'Brgy. Tacub', 'Brgy. Sibulan', 'Brgy. Maraga-a', 'Brgy. Kisulan'],
 'Magsaysay': ['Poblacion', 'Brgy. Bacungan', 'Brgy. Mabini', 'Brgy. Tagaytay', 'Brgy. Balnate', 'Brgy. Glamang', 'Brgy. Kanapulo', 'Brgy. New Opon'],
 'Malalag': ['Poblacion', 'Brgy. Baybay', 'Brgy. Bolton', 'Brgy. Bulacan', 'Brgy. Mabini', 'Brgy. Tagansule', 'Brgy. San Isidro', 'Brgy. Ibo'],
 'Matanao': ['Poblacion', 'Brgy. Kauswagan', 'Brgy. Camanchiles', 'Brgy. Saub', 'Brgy. San Jose', 'Brgy. Tamlangon', 'Brgy. Buas', 'Brgy. Kapok'],
 'Padada': ['Poblacion', 'Brgy. Piape', 'Brgy. Quirino', 'Brgy. Hinoba', 'Brgy. Almendras', 'Brgy. Harada', 'Brgy. Palili', 'Brgy. Upper Limonso'],
 'Santa Cruz': ['Poblacion (Zone 1)', 'Brgy. Astorga', 'Brgy. Bato', 'Brgy. Coronon', 'Brgy. Darong', 'Brgy. Inawayan', 'Brgy. Sibulan', 'Brgy. Tibolo'],
 'Sulop': ['Poblacion', 'Brgy. Balasiao', 'Brgy. Carre', 'Brgy. Harada', 'Brgy. Kiblagon', 'Brgy. Labon', 'Brgy. Roxas', 'Brgy. Waterfall']}
SPECIES = {'dog': (['Aspin (mixed breed)', 'Aspin (mixed breed)', 'Shih Tzu', 'Labrador mix', 'Beagle', 'German Shepherd mix', 'Pomeranian', 'Poodle mix', 'Dachshund mix', 'Husky mix'], ['brown', 'black', 'tan', 'golden', 'white', 'cream', 'grey'],
                 ['Brownie', 'Bantay', 'Choco', 'Bruno', 'Tiger', 'Blackie', 'Whitey', 'Snoopy', 'Duke', 'Pogi', 'Maya', 'Princess', 'Sam', 'Biscuit', 'Mango', 'Buddy', 'Rocky', 'Bella', 'Coco', 'Max']),
           'cat': (['Puspin (domestic shorthair)', 'Puspin (domestic shorthair)', 'Persian mix', 'Siamese mix', 'Orange Tabby', 'Bombay', 'Calico', 'Maine Coon mix'], ['grey', 'white', 'orange', 'black', 'cream', 'brown'],
                   ['Miming', 'Muning', 'Luna', 'Oreo', 'Simba', 'Nala', 'Garfield', 'Mocha', 'Ginger', 'Whiskers', 'Shadow', 'Mochi', 'Tomcat', 'Kitkat']),
           'rabbit': (['Holland Lop', 'Dwarf', 'Mini Rex', 'Netherland Dwarf'], ['white', 'brown', 'grey', 'cream'], ['Thumper', 'Peanut', 'Bunny', 'Cotton', 'Hopper', 'Snowy']),
           'bird': (['Parakeet', 'Lovebird', 'Cockatiel'], ['green', 'golden', 'orange'], ['Kiwi', 'Lora', 'Tweety', 'Mayang'])}
HIST = {'critical': ['Hit by a vehicle on the highway; surgery and stabilisation, now recovering.', 'Found weak and unable to stand; on IV fluids and close monitoring.', 'Severe wound found by a barangay tanod; emergency treatment given.'],
        'injured': ['Leg wound treated; healing well.', 'Torn ear and scratches from a fight; cleaned and medicated.', 'Limping after being hit by a tricycle; x-ray showed no break.', 'Wing or paw injury, now in recovery.'],
        'sick': ['Skin infection and mange; treated and groomed.', 'Respiratory infection; on antibiotics.', 'Underweight and dewormed; gaining weight on a feeding plan.', 'Tick fever treated; recovering.'],
        'healthy': ['Found as a stray; vaccinated and dewormed.', 'Surrendered by an owner who moved away; friendly and calm.', 'Rescued with littermates; spayed/neutered and ready for a home.', 'Abandoned near the market; very gentle with children.']}
FIRST = ['Maria', 'Jose', 'Ana', 'Carlo', 'Grace', 'Mark', 'Joy', 'Ramon', 'Liza', 'Paolo', 'Rina', 'Kim', 'Jun', 'Mica', 'Rey', 'Jessa', 'Noel', 'Cherry', 'Allan', 'Daisy', 'Ian', 'Faith', 'Bong', 'Lovely']
LAST = ['Santos', 'Reyes', 'Cruz', 'Bautista', 'Ocampo', 'Garcia', 'Mendoza', 'Torres', 'Villanueva', 'Ramos', 'Aquino', 'Castillo', 'Flores', 'Rivera', 'Dizon', 'Navarro', 'Salazar', 'Lumayag', 'Dacillo', 'Abella', 'Tumulak', 'Cabanilla']
VETS = ['Dr. Veterinarian', 'Dr. A. Villanueva', 'Dr. R. Ocampo']
def _ins(cur, t, **k):
    cur.execute(f"insert into {t}({','.join(k)}) values({','.join(['%s'] * len(k))})", tuple(k.values())); return cur.lastrowid
def _n(cur, sql):
    cur.execute(sql); r = cur.fetchone(); return r['n'] if isinstance(r, dict) else r[0]
def seed_areas(conn):
    """Adds the 10 Davao del Sur places the first time (only when the list is empty). Returns True if added."""
    cur = conn.cursor()
    if _n(cur, 'select count(*) n from service_areas'): return False
    for nm, kind, la, ln, r in AREAS: _ins(cur, 'service_areas', name=nm, kind=kind, lat=la, lng=ln, radius_km=r, note='Sample centre - move the pin if needed.')
    conn.commit(); return True
def seed(conn, force=False):
    """force=True adds the Davao del Sur sample set on top of an existing database (only once)."""
    cur = conn.cursor(); seed_areas(conn)
    if _n(cur, 'select count(*) n from animals') and not force: return False
    if _n(cur, f"select count(*) n from animals where notes='{MARK}'"): return False
    rng = random.Random(2026); up = os.path.join(HERE, 'static', 'uploads'); os.makedirs(up, exist_ok=True); t = date.today(); iso = lambda d: d.isoformat()
    cur.execute("select id from users where role='admin' order by id limit 1"); r = cur.fetchone(); uid = r['id'] if isinstance(r, dict) else r[0]
    cur.execute('select id,name,lat,lng from service_areas where active=1'); ar = {a['name']: a for a in cur.fetchall()}
    names = [a for a in AREAS if a[0] in ar] or AREAS
    def where():
        nm = rng.choice(names)[0]; a = ar.get(nm); pl = rng.choice(PLACES.get(nm, ['Poblacion'])); la, ln = (float(a['lat']), float(a['lng'])) if a else (6.7497, 125.3572)
        return (a['id'] if a else None), f'{pl}, {nm}', round(la + rng.uniform(-.022, .022), 6), round(ln + rng.uniform(-.022, .022), 6), nm
    def phone(): return f"09{rng.choice(['17', '18', '19', '27', '28', '35', '55'])}-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"
    def person(): f, l = rng.choice(FIRST), rng.choice(LAST); return f'{f} {l}', f'{f}.{l}'.lower().replace(' ', '') + '@example.com'
    def svg(fn, sp, col): open(os.path.join(up, fn), 'w').write(avatar(sp, C[col]))
    plan = ['dog'] * 20 + ['cat'] * 14 + ['rabbit'] * 6 + ['bird'] * 4; rng.shuffle(plan); used = {k: [] for k in SPECIES}; animals = []
    for i, sp in enumerate(plan):
        br, cols, nms = SPECIES[sp]; free = [x for x in nms if x not in used[sp]] or nms; nm = rng.choice(free); used[sp].append(nm); col = rng.choice(cols)
        cond = rng.choices(['healthy', 'injured', 'sick', 'critical'], [38, 28, 26, 8])[0]
        st = rng.choices(['available', 'under_care', 'adopted', 'released', 'deceased'], [44, 26, 16, 11, 3])[0]
        if st == 'available' and cond in ('critical', 'sick'): st = 'under_care'
        if cond == 'critical' and st in ('adopted', 'released'): st = 'under_care'
        ago = rng.randint(3, 120); d0 = t - timedelta(days=ago); aid, loc, la, ln, an = where(); hist = rng.choice(HIST[cond]); fn = f'demo_dds_{i + 1}.svg'; svg(fn, sp, col)
        age = rng.choice([0.3, 0.5, 1, 1, 2, 2, 3, 4, 5, 6, 8]) if sp != 'bird' else rng.choice([1, 2, 3])
        a = _ins(cur, 'animals', name=nm, species=sp.title(), breed=rng.choice(br), sex=rng.choice(['male', 'female']), age_years=age, color=col.title(), intake_date=iso(d0), status=st, medical_history=hist, notes=MARK, photo=fn)
        who, em = person()
        rid = _ins(cur, 'rescues', rescue_date=iso(d0), location=loc, species=sp.title(), description=f'{col} {sp}', animal_condition=cond, details=hist, reporter_name=who, reporter_contact=phone(), reporter_email=em, animal_id=a, reported_by=uid, photo=fn, lat=la, lng=ln, area_id=aid)
        cur.execute('update animals set rescue_id=%s where id=%s', (rid, a)); animals.append(dict(id=a, st=st, name=nm, area=an, d0=d0))
        vet = rng.choice(VETS); _ins(cur, 'medical_records', animal_id=a, record_type='examination', record_date=iso(d0 + timedelta(days=1)), details='Intake examination: weight, temperature and body condition recorded.', vet_name=vet, created_by=uid)
        fu = d0 + timedelta(days=30); _ins(cur, 'medical_records', animal_id=a, record_type='vaccination', record_date=iso(d0 + timedelta(days=7)), details='Core vaccination (anti-rabies) and deworming.', medication='Anti-rabies + combination vaccine' if sp in ('dog', 'cat') else 'Vitamin supplement',
                                           dosage='1 dose', vet_name=vet, followup_date=iso(fu), followup_done=1 if fu < t - timedelta(days=3) else 0, created_by=uid)
        if cond in ('critical', 'injured') and ago > 5: _ins(cur, 'medical_records', animal_id=a, record_type='treatment', record_date=iso(d0 + timedelta(days=2)), details='Wound cleaning, dressing and pain relief.', medication='Antibiotic + pain relief', dosage='2x daily, 7 days', vet_name=vet, created_by=uid)
        if st == 'under_care': _ins(cur, 'medical_records', animal_id=a, record_type='follow_up', record_date=iso(t - timedelta(days=rng.randint(1, 4))), details='Re-check: eating well, condition improving.', vet_name=vet, followup_date=iso(t + timedelta(days=rng.randint(1, 10))), created_by=uid)
    # open / recent reports that are not yet animals (some from the public form)
    kinds = [('new', 'public')] * 6 + [('responding', 'public')] * 3 + [('responding', 'staff')] + [('rescued', 'staff')] * 4 + [('closed', 'public')] * 4 + [('new', 'staff')] * 2
    for k, (cs, src) in enumerate(kinds):
        sp = rng.choice(['dog', 'dog', 'cat', 'cat', 'rabbit', 'bird']); col = rng.choice(SPECIES[sp][1]); cond = rng.choice(['injured', 'sick', 'healthy', 'critical']); aid, loc, la, ln, an = where(); fn = f'demo_dds_rep{k + 1}.svg'; svg(fn, sp, col); who, em = person()
        d = t - timedelta(days=0 if cs == 'new' else rng.randint(1, 25))
        _ins(cur, 'rescues', rescue_date=iso(d), location=loc, species=sp.title(), description=f'{col.title()} {sp}, {rng.choice(["no collar", "with a collar", "very thin", "scared and hiding", "with puppies/kittens nearby", "near the road"])}.', animal_condition=cond,
             details='Sent from the public "I found a pet" form.' if src == 'public' else 'Reported by phone.', reporter_name=who, reporter_contact=phone(), reporter_email=em, photo=fn, lat=la, lng=ln, area_id=aid, source=src, case_status=cs, reported_by=uid if src == 'staff' else None)
    ad = []
    for k in range(18):
        who, em = person(); aid, loc, la, ln, an = where()
        ad.append(_ins(cur, 'adopters', full_name=who, phone=phone(), email=em, address=loc, area_id=aid, household_notes=rng.choice(['Has a fenced yard; experienced pet owner.', 'Family with two kids; first time adopting.', 'Lives in a house with a small garden.', 'Works from home; has one other cat.', 'Rural home with a large lot.'])))
    for an_ in animals:
        if an_['st'] == 'adopted': _ins(cur, 'applications', animal_id=an_['id'], adopter_id=rng.choice(ad), status='completed', notes='Adopted after interview and home visit.', reviewed_by=uid, completed_at=iso(t - timedelta(days=rng.randint(5, 40))))
        elif an_['st'] == 'available' and rng.random() < .6:
            for _ in range(rng.choice([1, 1, 2])):
                s = rng.choices(['pending', 'approved', 'rejected'], [60, 20, 20])[0]; _ins(cur, 'applications', animal_id=an_['id'], adopter_id=rng.choice(ad), status=s, notes=rng.choice(['Wants an active pet.', 'Family with kids.', 'Second pet.', 'Lives near the barangay hall.']), reviewed_by=uid if s != 'pending' else None)
    for k in range(6):
        who, em = person(); aid, loc, la, ln, an = where(); sp = rng.choice(['dog', 'cat', 'rabbit']); col = rng.choice(SPECIES[sp][1]); fn = f'demo_dds_rh{k + 1}.svg'; svg(fn, sp, col)
        _ins(cur, 'rehome_requests', owner_name=who, contact=phone(), email=em, address=loc, area_id=aid, pet_name=rng.choice(SPECIES[sp][2]), species=sp.title(), breed=rng.choice(SPECIES[sp][0]), sex=rng.choice(['male', 'female']), age_years=rng.choice([1, 2, 3, 4]), color=col.title(),
             reason=rng.choice(['I am moving to a boarding house that does not allow pets.', 'I am going abroad for work.', 'Allergies in the family.', 'I can no longer afford the food and vet care.', 'Our new baby needs all our attention.']), health_notes='Vaccinated, friendly, used to children.', photo=fn, status='declined' if k == 5 else 'pending')
    for k, kind in enumerate(['foster', 'volunteer', 'both', 'volunteer', 'foster', 'volunteer', 'both', 'volunteer']):
        who, em = person(); aid, loc, la, ln, an = where(); s = ['pending', 'pending', 'approved', 'pending', 'declined', 'approved', 'pending', 'pending'][k]
        _ins(cur, 'volunteer_applications', kind=kind, full_name=who, email=em, phone=phone(), address=loc, area_id=aid, availability=rng.choice(['Weekends', 'Saturdays 8am-12pm', 'Weekday evenings', 'Any day after class']), experience=rng.choice(['Raised dogs and cats for 10 years.', 'Helped at a school animal club.', 'Veterinary technology student.', 'First time, very willing to learn.']),
             home_notes='House with a fenced yard.' if kind != 'volunteer' else None, animals_ok=rng.choice(['Dogs', 'Cats', 'Dogs and cats', 'Any']), status=s, reviewed_by=uid if s != 'pending' else None)
    sup = []
    for nm, key, unit, need, pr, note in [('Dog food (dry, adult)', 'food', 'sacks', 12, 'urgent', '20 kg sacks or any brand without added dyes'), ('Cat food (dry)', 'food', 'sacks', 8, 'high', 'Any brand, 1-7 kg bags'), ('Cat litter', 'litter', 'bags', 12, 'high', 'Unscented clumping litter'),
                                          ('Pet beds / blankets', 'bed', 'pcs', 10, 'normal', 'Washable, any size'), ('Leashes & collars', 'leash', 'pcs', 15, 'normal', None), ('Pet carriers', 'carrier', 'pcs', 4, 'high', 'For bringing rescues to the vet'),
                                          ('Chew toys', 'toys', 'pcs', 20, 'normal', None), ('Hay for rabbits', 'hay', 'bags', 6, 'normal', None), ('Anti-rabies vaccine fund (items)', 'vet', 'vials', 30, 'urgent', 'Bring vials or ask us for the vet clinic list'), ('Cages / kennels', 'cage', 'pcs', 6, 'high', 'Medium or large, for recovering animals'),
                                          ('Pet shampoo & grooming kit', 'groom', 'sets', 8, 'normal', None), ('Water bowls', 'water', 'pcs', 20, 'normal', 'Stainless steel preferred')]:
        sup.append(_ins(cur, 'supplies', name=nm, img_key=key, unit=unit, qty_needed=need, priority=pr, notes=note))
    for k in range(16):
        who, em = person(); s = rng.choices(['pending', 'confirmed', 'received'], [35, 30, 35])[0]
        _ins(cur, 'pledges', supply_id=rng.choice(sup), pledger_name=who, phone=phone(), email=em if rng.random() < .7 else None, qty=rng.randint(1, 4), status=s, dropoff_date=iso(t + timedelta(days=rng.randint(1, 6))) if s != 'received' else None, reviewed_by=uid if s != 'pending' else None)
    conn.commit(); return True
