# Animal Rescue & Adoption Management System (Flask + MySQL)

## 1. Install
Install MySQL 8 (or MariaDB) and Python 3.10+. In the VS Code terminal:

    python -m venv .venv
    .venv\Scripts\activate          (Mac/Linux: source .venv/bin/activate)
    pip install -r requirements.txt

## 2. Configure MySQL connection (defaults: localhost, user root, empty password, db animal_rescue)
Windows PowerShell:  $env:DB_PASSWORD="your_mysql_password"
Mac/Linux:           export DB_PASSWORD="your_mysql_password"
(Optional: DB_HOST, DB_PORT, DB_USER, DB_NAME, SECRET_KEY)

## 3. Create the database, tables and SAMPLE DATA (14 pets with pictures, rescues, medical records, adopters, applications)
    python init_db.py            (add --no-demo for an empty system; safe to re-run on an existing DB — it upgrades the tables and only adds samples if no animals exist)
or in MySQL Workbench / terminal:  `mysql -u root -p < schema.sql`  (then run `python init_db.py` to add the starter accounts)

## 4. Run
    python app.py      ->  http://127.0.0.1:5000   (public website)
                           http://127.0.0.1:5000/staff/login   (staff sign in - separate page, not in the public menu)

Starter logins (change them in Accounts): admin/Admin@123, staff1/Staff@123, vet1/Vet@12345, volunteer1/Volunteer@123

## Roles
admin: everything incl. accounts | staff: rescues, animals, medical, adoptions, reports | vet: rescues, animals, medical, reports | volunteer: report rescues, view animals

## New features
- Pet photos: upload on rescue/animal forms (PNG/JPG/GIF/WEBP, max 6 MB). Demo pets get generated portraits.
- Public homepage `/` with adoptable pets and an online adoption form (lands in Adoptions as *pending*).
- Background pictures: put your own photo at `static/img/hero.jpg` to replace the default hero artwork.
- Dashboard charts, card gallery of animals, adopter profiles, rescue editing, status change, print profile.

## Version 2 - new features
**Public pages (no login needed)**
- `/report-found` - **"I found a pet"**: anyone takes/uploads a photo, writes where the animal is (optional GPS button) and sends. It lands in *Rescues* as a **new public report** (red alert bar on the staff dashboard; filter Rescues by *Case status = new*). Staff set the case to responding / rescued / closed on the report page.
- `/rehome` - **"Rehome my pet"**: owners who want to put their pet up for adoption send the pet's details + photo. Staff review them in **Rehome requests** and press *Accept* to create the animal profile automatically (then set it to *Available* so it shows on the homepage).
- `/needs` - **Pet needs & supplies** guide with pictures (food, water, bed, leash/ID, carrier, litter, vet, grooming, toys, cage, hay), filtered per pet type. A preview is also on the homepage.

**Appearance**
- Dark mode toggle (moon/sun button in the header) for everyone; logged-in users keep it saved to their account.
- Background picture: the 🎨 button lets anyone pick a preset (meadow, sunset, ocean, night sky, bones & bowls). Logged-in users can also **upload their own background picture** in *My profile*.
- User profile (`/profile`, click your avatar): display name, profile picture, color mode, background, link to change password.

**Upgrade an existing database:** run `python init_db.py --no-demo` once - it adds the new tables/columns (users.avatar/bg/bgfile/theme, rescues.source/case_status, rehome_requests) without touching your data. Fresh installs: `python init_db.py` adds sample data including 2 public reports and 1 rehome request.


## Version 3 - what's new
**Look:** clean teal palette (no more orange); the ZIP artwork is kept and recolored. Public website and staff area are now separate layouts.

**Staff sign-in is its own page:** `/staff/login`. The public menu has no staff links (only a small "Staff sign in" in the footer). Staff get a sidebar menu and a global search box.

**Maps (Leaflet + OpenStreetMap, needs internet in the browser; default view = Cagayan de Oro)**
- `/report-found` and the staff rescue form have a big map: tap to drop a pin, drag to adjust, search a place, or "Use my location".
- `/map` (staff): all pinned rescue cases, colored by condition, bigger ring = still open, Street/Satellite switch, filters, clickable case list.
- Each rescue page shows its pin.

**Track request** `/track`: type the reference number (R-0012 rescue, AP-0003 adoption, RH-0001 rehome, VF-0002 volunteer/foster, PL-0004 pledge) + the phone or email used. Shows a status timeline. Wrong contact = nothing is revealed.

**Email when staff approve/decline:** adoption applications, rehome requests, volunteer/foster, supply pledges, and rescue case updates (if the reporter gave an email). Every message is saved in **Email log** (staff menu). To actually deliver, set SMTP before `python app.py`:

    MAIL_HOST=smtp.gmail.com  MAIL_PORT=587  MAIL_USER=you@gmail.com  MAIL_PASSWORD=<app password>  MAIL_FROM=you@gmail.com
    (optional: MAIL_SSL=1 for port 465, MAIL_TLS=0 to disable STARTTLS, ORG_NAME="Your shelter name")

Without these the system still works; messages are marked "not configured" in the Email log.

**Volunteer & foster applications** `/volunteer` (public) -> staff review in *Volunteer / foster* (approve/decline with an optional message).
**Supply wishlist & pledges** `/wishlist` (public) -> staff manage items in *Wishlist items* and confirm/receive pledges in *Pledges*. Items only - there is no online payment.
**Better search:** public `/pets` filters (name/breed/color, animal, sex, age); staff animal list (sort, sex, color, notes), rescue filters (source, "mine"), and global staff search (also jumps straight to e.g. `R-0012`).
**Case queues** `/queue`: open rescue cases (critical first, "Take case" assigns it to you), pending adoptions, rehome, volunteer/foster, pledges and follow-ups due. No automatic dispatch.
**CSV reports:** Reports page now covers rescues (with case status, source, latitude/longitude), animals, adoptions, medical records, volunteer/foster and pledges. Export CSV button on every report.
**About page** `/about`: objectives, system modules, technical components, human resource.

**Upgrade an existing database:** run `python init_db.py --no-demo` once (adds the new tables/columns, keeps your data).

## Roles (updated)
admin: everything incl. accounts | staff: all work incl. email log, volunteers, wishlist, pledges, reports | vet: rescues, queues, animals, medical, reports | volunteer: report rescues, view animals and the map


## v4 - new staff console design
- `icons.py` hand-drawn icon set (use `{{ icon('paw') }}` in any template)
- `static/staff.css` + `static/staff.js` staff design system (sidebar, top bar, bordered buttons, charts, sortable tables)
- Dashboard charts use real data only (6-month trend, status ring)
- Press `/` on any staff page to jump to search

## v4.1 - home page picture slideshow
- The teal hero panel is gone. The home page now opens with a full-width picture banner that slides automatically every 5 seconds (previous / next arrows, dots, pause button, swipe on phones, arrow keys).
- Pictures: `static/img/hero1.jpg`, `hero2.jpg`, `hero3.jpg`. Replace these files with your own (best: 1600 px wide, white or light background) or add a slide by copying one `<figure class="slide">` and one dot button in `templates/home.html`.
- Banner styles are at the bottom of `static/style.css` (search `home hero`).

## v4.2 - plain icons, bordered buttons, live notifications, Gmail
- **Icons** are plain black/white line icons everywhere (no emoji, no colors). **Every button, menu link and tab has a visible border.** To make the sidebar links borderless again, remove the `.staff .nl{border:...}` line at the bottom of `static/staff.css`.
- **Live notifications (staff):** the bell in the top bar shows how many requests are waiting. Every 8 seconds the page checks for new adoption applications, rescue reports, rehome requests, volunteer/foster applications and pledges. A new one pops up a toast with a "View" button (and a soft beep), and the browser tab title shows the count. Click the bell to see the latest list.
- **Gmail:** sign in as admin > *Email settings*. Enter the Gmail address and a Google **App Password** (Google Account > Security > 2-Step Verification > App passwords), then press *Save & send test email*. Settings are stored in `mail_settings.json` (private, not in git). After that the system emails applicants when staff approve/decline, and emails the "alert" address when the public sends a new request. Without it, nothing breaks; messages stay in the Email log.


## v4.5 - Worldwide map: the admin picks the allowed places, pins outside are invalid
- **Staff menu > Administration > Service areas > Add a place** now has **Find the place (worldwide)**. Type any barangay, municipality, city, region/province or country anywhere in the world, press *Find boundary*, pick the right result: its **real boundary** is saved and that whole place becomes allowed. The name and type are filled in for you (you can change them).
- Types: Country, Region / province, City, Municipality, Barangay, and *Other place (circle)* (old way: pin + distance in km, for a custom spot with no boundary). *Remove boundary* switches a place back to a circle.
- The public map (I found a pet) starts as a world map, shows only the places the admin has **Open**, and accepts a pin only **inside** them. A pin outside - or no pin at all - is refused on the page and again on the server.
- Place search uses OpenStreetMap Nominatim from the browser (needs internet; fine for light admin use). The saved boundary is simplified and stored in `service_areas.geojson`.
- Upgrade an existing database: `python init_db.py --no-demo` (adds the `geojson` column and the Region / Country types; your data stays). The 10 Davao del Sur places stay as circles until you re-add them with a boundary.

## v4.4 - Davao del Sur only: service areas + more sample data
**Service areas (admin only): staff menu > Administration > Service areas** (`/areas`)
- The admin decides which places the public may use. Add a place (name, type, drop a pin on the map for its center, and an accepted distance in km), edit it, **Close** it (hides it from the public forms, keeps the old records) or **Open** it again. A place that already has records cannot be deleted - close it instead.
- The public forms now have a required **Municipality / city** dropdown that lists only the *open* places: **I found a pet** (`/report-found`), **Rehome my pet**, **Volunteer & foster**, and the **Apply to adopt** form. The chosen place is added to the saved location/address and kept in `area_id`.
- On **I found a pet** the map shows the open places as circles. A pin outside every circle is refused (on the page and again on the server, so it cannot be bypassed), and the place search is limited to the area.
- If the admin closes every place, the public forms show a "closed" message instead of the form.
- Staff can still log any rescue themselves (staff forms are not restricted). Pledges/wishlist have no location, so they are not restricted.
- The 10 Davao del Sur places are added automatically: Digos City, Bansalan, Hagonoy, Kiblawan, Magsaysay, Malalag, Matanao, Padada, Santa Cruz, Sulop. **The center pins are approximate - open Service areas, look at the circles and move a pin if one is off.** To add Davao City or a barangay, use *Add a place*.

**Sample data (all in Davao del Sur):** 44 animals with portraits, 64 rescue reports (public + staff, new / responding / rescued / closed, pinned around the 10 places), medical records, 18 adopters, adoption applications, 6 rehome requests, 8 volunteer/foster applications, 12 wishlist items, 16 pledges. Names, phone numbers and emails are made up (emails use example.com, so nothing is sent to real people).
- Brand-new database: `python init_db.py`
- Start over with a clean Davao del Sur database (DELETES everything, asks you to type YES): `python init_db.py --reset`
- Keep your current data and just add the Davao del Sur samples on top (once only): `python init_db.py --more-demo`
- Upgrade only (adds the new table/columns and the 10 places, no samples): `python init_db.py --no-demo`
