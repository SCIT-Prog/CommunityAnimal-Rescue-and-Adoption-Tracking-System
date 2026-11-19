-- Animal Rescue & Adoption System — MySQL 8 schema
CREATE DATABASE IF NOT EXISTS animal_rescue CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE animal_rescue;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  full_name VARCHAR(100) NOT NULL,
  role ENUM('admin','staff','vet','volunteer') NOT NULL DEFAULT 'volunteer',
  pw_hash VARCHAR(255) NOT NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  avatar VARCHAR(255),
  bg VARCHAR(255),
  bgfile VARCHAR(255),
  theme VARCHAR(10),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS service_areas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  kind ENUM('city','municipality','barangay','region','country','place') NOT NULL DEFAULT 'municipality',
  lat DECIMAL(9,6) NOT NULL,
  lng DECIMAL(9,6) NOT NULL,
  radius_km DECIMAL(5,1) NOT NULL DEFAULT 12.0,
  active TINYINT(1) NOT NULL DEFAULT 1,
  note VARCHAR(255),
  geojson MEDIUMTEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS animals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  species VARCHAR(50) NOT NULL,
  breed VARCHAR(80),
  sex ENUM('male','female','unknown') DEFAULT 'unknown',
  age_years DECIMAL(4,1),
  color VARCHAR(50),
  intake_date DATE NOT NULL,
  status ENUM('under_care','available','adopted','released','deceased') NOT NULL DEFAULT 'under_care',
  medical_history TEXT,
  notes TEXT,
  rescue_id INT NULL,
  photo VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rescues (
  id INT AUTO_INCREMENT PRIMARY KEY,
  rescue_date DATE NOT NULL,
  location VARCHAR(200) NOT NULL,
  species VARCHAR(50) NOT NULL,
  description TEXT,
  animal_condition ENUM('critical','injured','sick','healthy') NOT NULL,
  reporter_name VARCHAR(100),
  reporter_contact VARCHAR(100),
  details TEXT,
  photo VARCHAR(255),
  lat DECIMAL(9,6) NULL,
  lng DECIMAL(9,6) NULL,
  reporter_email VARCHAR(120),
  assigned_to INT NULL,
  source ENUM('staff','public') NOT NULL DEFAULT 'staff',
  case_status ENUM('new','responding','rescued','closed') NOT NULL DEFAULT 'rescued',
  animal_id INT NULL,
  reported_by INT NULL,
  area_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (animal_id) REFERENCES animals(id) ON DELETE SET NULL,
  FOREIGN KEY (reported_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS medical_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  animal_id INT NOT NULL,
  record_type ENUM('examination','vaccination','treatment','medication','follow_up') NOT NULL,
  record_date DATE NOT NULL,
  details TEXT NOT NULL,
  medication VARCHAR(120),
  dosage VARCHAR(80),
  vet_name VARCHAR(100),
  followup_date DATE NULL,
  followup_done TINYINT(1) NOT NULL DEFAULT 0,
  created_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (animal_id) REFERENCES animals(id) ON DELETE CASCADE,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS adopters (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(120),
  phone VARCHAR(40) NOT NULL,
  address VARCHAR(255),
  area_id INT NULL,
  household_notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  animal_id INT NOT NULL,
  adopter_id INT NOT NULL,
  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status ENUM('pending','approved','rejected','completed','cancelled') NOT NULL DEFAULT 'pending',
  notes TEXT,
  reviewed_by INT NULL,
  completed_at DATE NULL,
  FOREIGN KEY (animal_id) REFERENCES animals(id) ON DELETE CASCADE,
  FOREIGN KEY (adopter_id) REFERENCES adopters(id) ON DELETE CASCADE,
  FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rehome_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  owner_name VARCHAR(100) NOT NULL,
  contact VARCHAR(100) NOT NULL,
  email VARCHAR(120),
  address VARCHAR(255),
  area_id INT NULL,
  pet_name VARCHAR(80) NOT NULL,
  species VARCHAR(50) NOT NULL,
  breed VARCHAR(80),
  sex ENUM('male','female','unknown') DEFAULT 'unknown',
  age_years DECIMAL(4,1),
  color VARCHAR(50),
  reason TEXT NOT NULL,
  health_notes TEXT,
  photo VARCHAR(255),
  status ENUM('pending','accepted','declined') NOT NULL DEFAULT 'pending',
  animal_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (animal_id) REFERENCES animals(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS volunteer_applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  kind ENUM('volunteer','foster','both') NOT NULL DEFAULT 'volunteer',
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL,
  phone VARCHAR(40) NOT NULL,
  address VARCHAR(255),
  area_id INT NULL,
  availability TEXT,
  experience TEXT,
  home_notes TEXT,
  animals_ok VARCHAR(150),
  status ENUM('pending','approved','declined') NOT NULL DEFAULT 'pending',
  staff_note TEXT,
  reviewed_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS supplies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  img_key VARCHAR(30) NOT NULL DEFAULT 'food',
  unit VARCHAR(30) NOT NULL DEFAULT 'pcs',
  qty_needed INT NOT NULL DEFAULT 1,
  priority ENUM('urgent','high','normal') NOT NULL DEFAULT 'normal',
  notes VARCHAR(255),
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pledges (
  id INT AUTO_INCREMENT PRIMARY KEY,
  supply_id INT NOT NULL,
  pledger_name VARCHAR(100) NOT NULL,
  phone VARCHAR(40) NOT NULL,
  email VARCHAR(120),
  qty INT NOT NULL DEFAULT 1,
  dropoff_date DATE NULL,
  note VARCHAR(255),
  status ENUM('pending','confirmed','received','declined') NOT NULL DEFAULT 'pending',
  reviewed_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (supply_id) REFERENCES supplies(id) ON DELETE CASCADE,
  FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS email_log (
  id INT AUTO_INCREMENT PRIMARY KEY,
  to_email VARCHAR(120) NOT NULL,
  subject VARCHAR(200) NOT NULL,
  body TEXT,
  ref VARCHAR(20),
  status ENUM('sent','failed','not_configured') NOT NULL,
  error VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_animals_status ON animals(status);
CREATE INDEX idx_rescues_date ON rescues(rescue_date);
CREATE INDEX idx_med_followup ON medical_records(followup_date, followup_done);
CREATE INDEX idx_app_status ON applications(status);
CREATE INDEX idx_rehome_status ON rehome_requests(status);
CREATE INDEX idx_vol_status ON volunteer_applications(status);
CREATE INDEX idx_pledge_status ON pledges(status);
CREATE INDEX idx_rescue_geo ON rescues(case_status, lat, lng);
